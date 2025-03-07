## Work in progress, but wasted too much of my time already

from typing import Optional, Any, get_origin, get_args
from pydantic import BaseModel, Field, field_validator, field_serializer
import json


class SQLBoolean:
    """A special class to represent "TRUE" and "FALSE" literals in JSON, not as strings."""
    def __init__(self, value):
        if isinstance(value, str):
            self.value = value.lower() in ("true", "1", "yes", "y", "on")
        else:
            self.value = bool(value)
    
    def __bool__(self):
        return self.value
    
    def __str__(self) -> str:
        return "TRUE" if self.value else "FALSE"
    
    def __repr__(self) -> str:
        return f"BooleanLiteral({self.value})"
    
    def __eq__(self, other):
        if isinstance(other, SQLBoolean):
            return self.value == other.value
        return self.value == bool(other)


class SQLBaseModel(BaseModel):
    """Base model with custom JSON serialization for boolean fields."""
    
    model_config = {
        "arbitrary_types_allowed": True,
    }
    
    @field_validator('*', mode='before')
    @classmethod
    def validate_boolean_literals(cls, v, info):
        field_info = cls.model_fields.get(info.field_name)
        if not field_info:
            return v
            
        # Get the field type
        field_type = field_info.annotation
        
        # Handle Optional[BooleanLiteral]
        if get_origin(field_type) is Optional:
            args = get_args(field_type)
            if args and args[0] is SQLBoolean:
                if v is None:
                    return None
                return SQLBoolean(v)
                
        # Handle direct BooleanLiteral
        if field_type is SQLBoolean:
            return SQLBoolean(v)

        # Handle bool fields - convert them to BooleanLiteral
        if field_type is bool:
            return SQLBoolean(v)
            
        return v
    
    @field_serializer('*')
    def serialize_boolean_literals(self, v, info):
        if isinstance(v, SQLBoolean):
            return str(v)  # Returns "TRUE" or "FALSE"
        return v
    
    def model_dump_json(self, **kwargs):
        """Custom JSON serialization that replaces "TRUE" and "FALSE" with literals."""
        json_str = super().model_dump_json(**kwargs)
        # Create a non-standard JSON with TRUE and FALSE as literals
        # Note: This is not standard JSON and may not be parseable by all JSON parsers
        return json_str.replace('"TRUE"', 'TRUE').replace('"FALSE"', 'FALSE')


# Custom encoder that returns TRUE and FALSE literals without quotes
class CustomJSONEncoder(json.JSONEncoder):
    def encode(self, obj):
        if isinstance(obj, dict):
            # Handle dictionaries with BooleanLiteral values
            result = super().encode(obj)
            return result.replace('"TRUE"', 'TRUE').replace('"FALSE"', 'FALSE')
        return super().encode(obj)
    
    def default(self, obj):
        if isinstance(obj, SQLBoolean):
            return str(obj)
        return super().default(obj)


########################
# Testing
########################

if __name__ == "__main__":
    # Create an instance
    class Foo(SQLBaseModel):
        is_deleted: SQLBoolean = Field(default=False, description="Soft delete flag (Default False)")
        is_test: bool = Field(default=True, description="Test flag")


    record = Foo()
    
    # Standard JSON serialization (will have quotes around TRUE/FALSE)
    standard_json = json.dumps(record.model_dump())
    print(f"Standard JSON: {standard_json}")
    
    # Custom JSON serialization (TRUE/FALSE without quotes)
    custom_json = record.model_dump_json()
    print(f"Custom JSON: {custom_json}")
    
    # Using the custom encoder
    custom_encoded = json.dumps(record.model_dump(), cls=CustomJSONEncoder)
    print(f"Custom encoded: {custom_encoded}")
    
    # Boolean logic still works
    if not record.is_deleted:
        print("Record is not deleted")