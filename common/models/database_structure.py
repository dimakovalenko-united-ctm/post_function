#!/usr/bin/env python
from pydantic import BaseModel, Field, field_validator
from typing import Any, Optional, Type
from common.models.approved_uuid import ApprovedUUID as UUID

from typing import Optional, Dict, Any
from common.models.date_time_iso8601 import ApprovedDateTime as DateTime

# Define the default columns
default_columns = [
    'timestamp', 'open', 'close', 'high', 'low',
    'volume', 'fiat_currency', 'crypto_symbol'
]

class AllAllowedQueryReturns(BaseModel):
    id: Optional[UUID] = Field(None, description="GUID, uses BigQuery GENERATE_UUID function")
    crypto_name: Optional[str] = Field(None, description="Name of the Crypto Currency")
    crypto_symbol: Optional[str] = Field(None, description="Symbol for the crypto currency")
    fiat_currency: Optional[str] = Field(None, description="Currency the values stored in such as USD or EUR")
    open: Optional[float] = Field(None, description="Open price")
    close: Optional[float] = Field(None, description="Close price")
    high: Optional[float] = Field(None, description="High price")
    low: Optional[float] = Field(None, description="Low price")
    volume: Optional[float] = Field(None, description="Volume")
    timestamp: Optional[DateTime] = Field(None, description="Timestamp at the point of insertion into table")
    is_deleted: Optional[str] = Field(None, description="Soft delete flag")
    
class DefaultQueryReturn(AllAllowedQueryReturns):
    """
    DefaultQueryReturn provides a fallback mechanism for query returns.
    If no fields are specified by the user, it defaults to `default_columns`.
    """
    @classmethod
    def get_default(cls) -> Dict[str, Any]:
        """
        Returns a dictionary with default column names and their default values (None).
        """
        return {field: None for field in default_columns}

    @classmethod
    def from_user_input(cls, user_fields: Optional[Dict[str, Any]] = None) -> "DefaultQueryReturn":
        """
        Creates a DefaultQueryReturn instance based on user input.
        If no user input is provided, falls back to default_columns.
        """
        # Use user-provided fields or fall back to default_columns
        fields = user_fields if user_fields is not None else cls.get_default()
        
        # Ensure only valid fields are included
        valid_fields = {key: value for key, value in fields.items() if key in cls.__fields__}
        
        # Create and return an instance of DefaultQueryReturn
        return cls(**valid_fields)


class OptionalFields(BaseModel):    
    timestamp: Optional[DateTime] = Field(..., description="ISO 8601 timestamp. [Default] - Current timestamp, can be overwritten with any past valid date.")
    dividends: Optional[float] = Field(default=0.0, description="Dividends. [Default] to 0.0 if not provided.")
    stock_splits: Optional[float] = Field(default=0.0, description="Stock Splits. [Default] to 0.0 if not provided.")
    metadata: Optional[str] = Field(default=None, description="String encoded JSON with no strict structure.")

class RequiredFields(BaseModel):    
    crypto_name: str = Field(..., description="Name of the Crypto Currency")
    crypto_symbol: str = Field(..., description="Symbol for the crypto currency")
    fiat_currency: str = Field(..., description="Currency the values stored in such as USD or EUR")
    source: str = Field(..., description="Source where the data was pulled from")
    open: float = Field(..., description="Open price")
    close: float = Field(..., description="Close price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    volume: float = Field(..., description="Volume")
    ticker: str = Field(..., description="Ticker used to look up the currency")


class AutoGeneratedFields(BaseModel):
    id: UUID                       = Field(..., description="UUID v4 of the inserted row")
    is_deleted: str                = Field(default="null", description="Soft delete flag (Default False)")
    insertion_timestamp: DateTime  = Field(..., description="ISO 8601 timestamp. Current timestamp, for the record")
    


class DatabaseStructure(RequiredFields, AutoGeneratedFields, OptionalFields):
    pass

