#!/usr/bin/env python
from sqlalchemy import create_engine, select, table, Column, func, and_, bindparam, text, cast, TIMESTAMP
import sqlalchemy_bigquery  # noqa: F401
from common.models.time_intervals import TimeInterval
from common.logging_utils import error, debug
from common.models.database_structure import (
    AllAllowedQueryReturns, DefaultQueryReturn
)
from datetime import datetime

class GetAllPrices():
    def __init__(self, dataset_id: str,
                 table_id: str, 
                 project_id: str,
                 columns: AllAllowedQueryReturns = None, 
                 time_interval: TimeInterval = TimeInterval.MINUTE):

        self.dataset_id = dataset_id
        self.table_id = table_id
        self.columns = columns if columns else DefaultQueryReturn.from_user_input()
        self.time_interval = time_interval
        self.project_id = project_id
        self.engine = create_engine(f'bigquery://{self.project_id}')

    def query(self, params) -> list:
        # Define table and columns dynamically
        table_name = f"{self.dataset_id}.{self.table_id}"
        cols_needed = self.columns.__fields__.keys()  # Now includes 'is_deleted'
        price_table = table(table_name, *[Column(col_name) for col_name in cols_needed])

        # Build window function for ROW_NUMBER
        interval = self.time_interval.value
        
        # Cast timestamp to TIMESTAMP type before using TIMESTAMP_TRUNC
        timestamp_col = cast(price_table.c.timestamp, TIMESTAMP)
        timestamp_trunc = func.TIMESTAMP_TRUNC(
            timestamp_col,
            text(interval)
        )
        
        row_number = func.ROW_NUMBER().over(
            partition_by=timestamp_trunc,
            order_by=price_table.c.timestamp.desc()
        ).label('rn')

        # Base query with common filters
        base_query = select(*price_table.c, row_number).where(
            and_(
                price_table.c.is_deleted.isnot(True),  # Now valid
                price_table.c.timestamp.between(bindparam('start_date'), bindparam('end_date'))
            )
        )

        # Apply optional filters
        if params.crypto_symbol:
            base_query = base_query.where(price_table.c.crypto_symbol == bindparam('crypto_symbol'))
        if params.fiat_currency:
            base_query = base_query.where(price_table.c.fiat_currency == bindparam('fiat_currency'))

        # Create CTE and final query
        cte = base_query.cte('IntervalData')
        
        # Exclude both 'rn' and 'is_deleted' from the final output
        columns_to_select = [
            getattr(cte.c, col_name) 
            for col_name in cols_needed 
            if col_name not in ('rn', 'is_deleted')
        ]
        
        final_query = (
            select(*columns_to_select)
            .select_from(cte)
            .where(cte.c.rn == 1)
            .order_by(cte.c.timestamp)
        )

        try:
            with self.engine.connect() as connection:
                result_proxy = connection.execute(final_query, {
                    'start_date': params.start_date.isoformat(),
                    'end_date': params.end_date.isoformat(),
                    'crypto_symbol': params.crypto_symbol,
                    'fiat_currency': params.fiat_currency,
                })
                
                # Convert results to list of dicts
                results = []
                for row in result_proxy:
                    # Try using _mapping first (SQLAlchemy 2.0+)
                    try:
                        row_dict = dict(row._mapping)
                    except AttributeError:
                        # Fall back to manual conversion
                        try:
                            row_dict = {}
                            for col_name, value in zip(row._fields, row):
                                row_dict[col_name] = value
                        except AttributeError:
                            # Last resort for older SQLAlchemy versions
                            row_dict = dict(row)
                            
                    results.append(row_dict)

                # Format timestamps and floats
                formatted_results = []
                for row in results:
                    formatted_row = {}
                    for key, value in row.items():
                        if isinstance(value, datetime):
                            formatted_row[key] = value.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        elif isinstance(value, float):
                            formatted_row[key] = f"{value:.10f}"
                        else:
                            formatted_row[key] = value
                    formatted_results.append(formatted_row)

                debug(f"Query Results: {formatted_results}")
                return formatted_results

        except Exception as e:
            error(e)
            raise e