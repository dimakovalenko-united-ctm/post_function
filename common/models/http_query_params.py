#!/usr/bin/env python
import pytz
from datetime import timedelta, timezone
from pydantic import BaseModel, field_validator, ConfigDict, Field
from fastapi import Query
from common.models.time_intervals import TimeInterval
from common.models.date_time_iso8601 import ApprovedDateTime as DateTime
from common.models.database_structure import AllAllowedQueryReturns, OptionalFields, RequiredFields
from typing import Optional, List, Any

class HttpQueryParams(AllAllowedQueryReturns):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    columns: Optional[List[str]] = Query(None, description="Specific columns to return")
    
    start_date: Optional[DateTime] = Query(
        None,
        description="Start date in YYYY-MM-DDTHH:mm:ssZ format in UTC"
    )
    end_date: Optional[DateTime] = Query(
        None,
        description="End date in YYYY-MM-DDTHH:mm:ssZ format in UTC"
    )
    interval: Optional[TimeInterval] = Query(
        default=TimeInterval.MINUTE,
        description="Time interval for data aggregation"
    )
    interval_value: int = Query(
        default=1,
        ge=1,
        description="Number of interval units"
    )
    output_format: Optional[str] = Query(
        default="json",
        regex="^(json|xml|csv)$",
        description="Output format (json, xml, or csv)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        
        # Set default start_date to 24 hours ago in UTC
        if self.start_date is None:
            self.start_date = DateTime.now().subtract_time(hours=24)
        
        # Set default end_date to now in UTC
        if self.end_date is None:
            self.end_date = DateTime.now(pytz.UTC).replace(tzinfo=timezone.utc)

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_individual_dates(cls, v, info):
        """
        Validate individual dates to ensure they are not in the future.
        
        Args:
            v: The date to validate
            info: Validation context information
        
        Returns:
            Validated DateTime instance
        
        Raises:
            ValueError if the date is in the future
        """
        if v is not None:
            # Ensure the input is a DateTime
            timestamp = v if isinstance(v, DateTime) else DateTime(v)
            
            # Check if the date is in the future
            if timestamp.in_future():
                raise ValueError(f"{info.field_name} cannot be in the future")
            
            return timestamp
        return v  # Return as-is if None

    @field_validator('end_date', mode='after')
    @classmethod
    def validate_date_range(cls, v, info):
        """
        Comprehensive date range validation with smart defaults.
        
        Args:
            v: The end date to validate
            info: Validation context information
        
        Returns:
            Validated end date
        
        Raises:
            ValueError if date range is invalid
        """
        # Get the current values from the model being validated
        values = info.data
        
        # Get the current UTC now time
        now = DateTime.now()
        
        # Check start_date
        start_date = values.get('start_date')
        
        # If start_date is provided, validate it
        if start_date is not None:
            # Ensure start_date is a DateTime
            start_date = start_date if isinstance(start_date, DateTime) else DateTime(start_date)
            
            # Validate start_date is not in the future
            if start_date.in_future():
                raise ValueError("Start date cannot be in the future")
        
        # Handle end_date logic
        if v is not None:
            # Ensure end_date is a DateTime
            end_date = v if isinstance(v, DateTime) else DateTime(v)
            
            # Validate end_date is not in the future
            if end_date.in_future():
                raise ValueError("End date cannot be in the future")
            
            # If start_date wasn't provided, set a default 24 hours before end_date
            if start_date is None:
                start_date = DateTime(end_date.to_datetime() - timedelta(hours=24))
        
        # If only start_date is provided, set end_date to 24 hours after start_date
        elif start_date is not None:
            v = DateTime(start_date.to_datetime() + timedelta(hours=24))
        
        # If both dates are provided, validate the range
        if start_date is not None and v is not None:
            # Ensure dates are DateTime
            start_date = start_date if isinstance(start_date, DateTime) else DateTime(start_date)
            end_date = v if isinstance(v, DateTime) else DateTime(v)
            
            # Convert to datetime for comparison
            start_dt = start_date.to_datetime()
            end_dt = end_date.to_datetime()
            
            # Check that end date is after start date
            if end_dt < start_dt:
                raise ValueError("End date must be after start date")
            
            # Check date range
            date_range = end_dt - start_dt
            if date_range.days > 30:
                raise ValueError("Date range cannot exceed 30 days")
        
        return v  # Return end_date

class OptionalFieldsModified(OptionalFields):
    """Extended OptionalFields with metadata guaranteed to be empty string instead of None"""
    metadata: str = Field(default="", description="String encoded JSON with no strict structure.")

class PostData(RequiredFields, OptionalFieldsModified):
    """
    Data model for POST requests. 
    Ensures metadata is always a string, never null to comply with AVRO schema.
    """
    pass