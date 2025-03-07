from datetime import datetime, timezone, timedelta
from typing import Any, Self, Union, Optional, Type

from dateutil import parser
from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler, validator
from pydantic_core import CoreSchema, core_schema
import json

class ApprovedDateTime(str):
    """
    An enhanced DateTime class that provides:
    - Validation for ISO-8601 format
    - Consistent serialization
    - Pydantic v3 compatibility
    - UTC now() method
    - Comparison methods
    - in_past() and in_future() methods
    """

    def __new__(
        cls, 
        value: Union[str, datetime, 'ApprovedDateTime', None] = None
    ) -> Self:
        """
        Create a new ApprovedDateTime instance.
        
        Args:
            value: Input to convert to an ISO-8601 formatted datetime string
                   Defaults to current UTC time if no value is provided
        
        Returns:
            An ApprovedDateTime instance
        
        Raises:
            ValueError: If the input cannot be parsed to a valid datetime
        """
        # If no value is provided, use current UTC time
        if value is None:
            value = datetime.now(timezone.utc)

        # Handle different input types
        if isinstance(value, datetime):
            # Ensure timezone awareness, defaulting to UTC if not provided
            dt = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        elif isinstance(value, ApprovedDateTime):
            dt = parser.isoparse(str(value))
        else:
            try:
                # Parse the input string, enforcing strict YYYY-MM-DD format if provided
                if isinstance(value, str):
                    try:
                        dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except ValueError:
                        # Fallback to general ISO-8601 parsing
                        dt = parser.isoparse(str(value))
                else:
                    dt = parser.isoparse(str(value))
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid datetime format. Must be YYYY-MM-DD or ISO-8601: {value}") from e
        
        # Convert to ISO-8601 format string
        iso_str = dt.isoformat()
        
        # Create the instance using __new__
        return super().__new__(cls, iso_str)

    @classmethod
    def now(cls, tz: Optional[Union[timezone, str]] = None) -> Self:
        """
        Create an ApprovedDateTime with the current time.
        
        Args:
            tz: Timezone to use. Defaults to UTC.
                Can be a timezone object or a timezone string.
        
        Returns:
            ApprovedDateTime instance with current time
        """
        # If tz is a string, convert to timezone object
        if isinstance(tz, str):
            try:
                from zoneinfo import ZoneInfo
                tz = ZoneInfo(tz)
            except ImportError:
                raise ValueError("zoneinfo module required to use timezone strings")
        
        # Use UTC if no timezone provided
        if tz is None:
            tz = timezone.utc
        
        return cls(datetime.now(tz))

    def isoformat(
        self, 
        sep: str = 'T', 
        timespec: str = 'auto', 
        tzone: bool = True
    ) -> str:
        """
        Return the date formatted according to ISO 8601 format.
        
        Args:
            sep: Separator between date and time. Defaults to 'T'.
            timespec: Specifies the precision of the time component. 
                      Defaults to 'auto'.
            tzone: Whether to include timezone information. Defaults to True.
        
        Returns:
            ISO 8601 formatted datetime string
        """
        # Parse the stored string into a datetime object
        dt = self.to_datetime()
        
        # Use the datetime.isoformat() method with provided parameters
        return dt.isoformat(sep=sep, timespec=timespec)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, 
        _source_type: type[Any], 
        _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """
        Provide a custom Pydantic core schema for validation and serialization.
        """
        return core_schema.union_schema([
            # Allow string input
            core_schema.str_schema(),
            # Allow direct datetime input
            core_schema.is_instance_schema(datetime),
            # Allow None for default value
            core_schema.none_schema(),
            # Custom validation schema
            core_schema.no_info_plain_validator_function(cls.validate)
        ])

    @classmethod
    def validate(cls, value: Any) -> Self:
        """
        Validate and convert input to an ApprovedDateTime instance.
        """
        return cls(value)

    def to_datetime(self) -> datetime:
        """
        Convert to a datetime object.
        
        Returns:
            A timezone-aware datetime object in UTC
        """
        return parser.isoparse(str(self))

    def to_dict(self) -> dict:
        """
        Convert datetime to a dictionary representation.
        """
        return {"datetime": str(self)}

    def to_json(self) -> str:
        """
        Convert datetime to a JSON string.
        """
        return json.dumps(str(self))

    def __repr__(self) -> str:
        """
        Provide a clear representation of the datetime.
        """
        return f"ApprovedDateTime('{self}')"

    def __hash__(self) -> int:
        """
        Make the ApprovedDateTime hashable.
        """
        return hash(str(self))

    def replace(self, tzinfo: Optional[timezone] = None) -> 'ApprovedDateTime':
        """
        Replace the timezone of the datetime.
        
        Args:
            tzinfo: New timezone to replace the current one
        
        Returns:
            A new ApprovedDateTime with the replaced timezone
        """
        dt = self.to_datetime()
        if tzinfo is not None:
            dt = dt.replace(tzinfo=tzinfo)
        return ApprovedDateTime(dt)

    def in_past(self, reference_time: Optional[Union[str, datetime, 'ApprovedDateTime']] = None) -> bool:
        """
        Check if this datetime is in the past.
        
        Args:
            reference_time: Optional reference time to compare against. 
                            Defaults to current time if not provided.
        
        Returns:
            True if the datetime is in the past, False otherwise
        """
        # Use current time as reference if not provided
        if reference_time is None:
            reference_time = self.now()
        
        # Convert reference time to datetime
        ref_dt = ApprovedDateTime(reference_time).to_datetime()
        
        # Compare this datetime to the reference
        return self.to_datetime() < ref_dt

    def subtract_time(self, days=0, hours=0, minutes=0, seconds=0) -> 'ApprovedDateTime':
        """
        Subtract time from this datetime.
        
        Args:
            days: Number of days to subtract
            hours: Number of hours to subtract
            minutes: Number of minutes to subtract
            seconds: Number of seconds to subtract
        
        Returns:
            A new ApprovedDateTime with the subtracted time
        """
        dt = self.to_datetime()
        delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        result_dt = dt - delta
        return ApprovedDateTime(result_dt)    

    def in_future(self, reference_time: Optional[Union[str, datetime, 'ApprovedDateTime']] = None) -> bool:
        """
        Check if this datetime is in the future.
        
        Args:
            reference_time: Optional reference time to compare against. 
                            Defaults to current time if not provided.
        
        Returns:
            True if the datetime is in the future, False otherwise
        """
        # Use current time as reference if not provided
        if reference_time is None:
            reference_time = self.now()
        
        # Convert reference time to datetime
        ref_dt = ApprovedDateTime(reference_time).to_datetime()
        
        # Compare this datetime to the reference
        return self.to_datetime() > ref_dt

    def is_future(self, reference_time: Optional[Union[str, datetime, 'ApprovedDateTime']] = None) -> bool:
        """
        Alias for in_future() to maintain compatibility with some validation patterns.
        
        Args:
            reference_time: Optional reference time to compare against. 
                            Defaults to current time if not provided.
        
        Returns:
            True if the datetime is in the future, False otherwise
        """
        return self.in_future(reference_time)

    def __lt__(self, other: Union[str, datetime, 'ApprovedDateTime']) -> bool:
        """Less than comparison"""
        return self.to_datetime() < ApprovedDateTime(other).to_datetime()

    def __le__(self, other: Union[str, datetime, 'ApprovedDateTime']) -> bool:
        """Less than or equal to comparison"""
        return self.to_datetime() <= ApprovedDateTime(other).to_datetime()

    def __gt__(self, other: Union[str, datetime, 'ApprovedDateTime']) -> bool:
        """Greater than comparison"""
        return self.to_datetime() > ApprovedDateTime(other).to_datetime()

    def __ge__(self, other: Union[str, datetime, 'ApprovedDateTime']) -> bool:
        """Greater than or equal to comparison"""
        return self.to_datetime() >= ApprovedDateTime(other).to_datetime()

    def __eq__(self, other: Union[str, datetime, 'ApprovedDateTime']) -> bool:
        """Equality comparison"""
        return self.to_datetime() == ApprovedDateTime(other).to_datetime()

# Example usage model to demonstrate serialization
class ExampleModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    created_at: ApprovedDateTime = Field(
        default_factory=ApprovedDateTime.now,
        description="Timestamp of creation in ISO-8601 format"
    )
    name: str
    start_date: Optional[ApprovedDateTime] = None
    end_date: Optional[ApprovedDateTime] = None

    @validator('start_date', 'end_date')
    def validate_dates(cls, v):
        """
        Example validator demonstrating date validation
        """
        if v is not None:
            # Check if the date is in the future
            if v.is_future():
                raise ValueError("Date cannot be in the future")
            return v
        return v  # Return as-is if None

    @validator('end_date')
    def validate_date_range(cls, v, values):
        """
        Example validator for date range checks
        """
        if v is not None and 'start_date' in values and values['start_date'] is not None:
            # Ensure both dates are in the same timezone for comparison
            v_utc = v.replace(tzinfo=timezone.utc)
            start_date_utc = values['start_date'].replace(tzinfo=timezone.utc)
            
            if v_utc < start_date_utc:
                raise ValueError("End date must be after start date")
            
            date_range = v_utc.to_datetime() - start_date_utc.to_datetime()
            if date_range.days > 30:
                raise ValueError("Date range cannot exceed 30 days")
        return v  # Return as-is if None




def example_usage():
    print("=== Basic Instantiation Examples ===")
    # Demonstrate various input types
    print("1. Current time (default):")
    dt1 = ApprovedDateTime()
    print(f"  Default UTC now: {dt1}")

    print("\n2. String inputs:")
    # Various string input formats
    date_strings = [
        "2023-12-31",  # Date only
        "2023-12-31T23:59:59Z",  # Full ISO 8601
        "2023-12-31T23:59:59+00:00",  # ISO 8601 with explicit UTC
        "2023-12-31 23:59:59",  # Space separator
        "2024-02-29",  # Leap year
    ]
    for s in date_strings:
        try:
            dt = ApprovedDateTime(s)
            print(f"  {s}: {dt}")
        except ValueError as e:
            print(f"  Error parsing {s}: {e}")

    print("\n3. Datetime object inputs:")
    # Datetime object inputs
    dt_obj = datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    naive_dt_obj = datetime(2023, 12, 31, 23, 59, 59)
    dt_from_obj = ApprovedDateTime(dt_obj)
    dt_from_naive_obj = ApprovedDateTime(naive_dt_obj)
    print(f"  With timezone: {dt_from_obj}")
    print(f"  Without timezone: {dt_from_naive_obj}")

    print("\n4. Comparison Methods:")
    # Comparison demonstrations
    now = ApprovedDateTime()
    past = ApprovedDateTime("2020-01-01")
    future = ApprovedDateTime("2030-01-01")
    
    print(f"  Current time: {now}")
    print(f"  Past time: {past}")
    print(f"  Future time: {future}")
    
    print("\n  Comparison tests:")
    print(f"  {past} < {now}: {past < now}")
    print(f"  {now} <= {now}: {now <= now}")
    print(f"  {future} > {now}: {future > now}")
    print(f"  {now} >= {now}: {now >= now}")
    print(f"  {now} == {now}: {now == now}")
    
    print("\n5. Past and Future Checks:")
    print(f"  Is {past} in past? {past.in_past()}")
    print(f"  Is {now} in past? {now.in_past()}")
    print(f"  Is {future} in future? {future.in_future()}")
    
    print("\n6. Timezone Demonstrations:")
    try:
        from zoneinfo import ZoneInfo
        # Create datetime in different timezones
        ny_time = ApprovedDateTime.now('America/New_York')
        tokyo_time = ApprovedDateTime.now('Asia/Tokyo')
        
        print("  New York time:", ny_time)
        print("  Tokyo time:", tokyo_time)
    except ImportError:
        print("  Timezone string support requires zoneinfo module")
    
    print("\n7. Timezone Replacement:")
    current_time = ApprovedDateTime.now()
    eastern_time = current_time.replace(tzinfo=timezone(timedelta(hours=-5)))
    print(f"  Current time: {current_time}")
    print(f"  Eastern time: {eastern_time}")
    
    print("\n8. Pydantic Model Validation Scenarios:")
    print("  a) Standard Model Creation:")
    standard_model = ExampleModel(
        name="Standard Test",
        start_date=ApprovedDateTime("2024-01-01"),
        end_date=ApprovedDateTime("2024-01-15")
    )
    print(f"    Created model with dates: {standard_model}")
    
    print("\n  b) Future Date Validation:")
    try:
        future_model = ExampleModel(
            name="Future Test",
            start_date=ApprovedDateTime("2100-01-01"),
            end_date=ApprovedDateTime("2100-01-02")
        )
    except ValueError as e:
        print(f"    Validation Error (Future Date): {e}")
    
    print("\n  c) Invalid Date Range:")
    try:
        invalid_range_model = ExampleModel(
            name="Invalid Range Test",
            start_date=ApprovedDateTime("2024-01-01"),
            end_date=ApprovedDateTime("2024-03-15")  # More than 30 days apart
        )
    except ValueError as e:
        print(f"    Validation Error (Date Range): {e}")

    print("\n=== Comprehensive Testing Complete ===")

if __name__ == "__main__":
    example_usage()