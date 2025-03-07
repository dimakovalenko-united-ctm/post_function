from typing import Any, Self, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
import json

class ApprovedUUID(str):
    """
    An enhanced UUID class that provides improved serialization 
    and validation capabilities for Pydantic v2/v3.
    """
    
    def __new__(cls, value: Union[str, UUID, 'ApprovedUUID']) -> Self:
        """
        Create a new ApprovedUUID instance.
        
        Args:
            value: Input to convert to a UUID string
        
        Returns:
            An ApprovedUUID instance
        
        Raises:
            ValueError: If the input cannot be converted to a valid UUID
        """
        # Convert input to standard UUID string
        if isinstance(value, UUID):
            uuid_str = str(value)
        elif isinstance(value, ApprovedUUID):
            uuid_str = str(value)
        else:
            # Validate the UUID string
            try:
                # This will raise ValueError if invalid
                uuid_obj = UUID(str(value))
                uuid_str = str(uuid_obj)
            except ValueError:
                raise ValueError(f"Invalid UUID: {value}")
        
        # Create the instance using __new__
        return super().__new__(cls, uuid_str)

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
            # Allow direct UUID input
            core_schema.is_instance_schema(UUID),
            # Custom validation schema
            core_schema.no_info_plain_validator_function(cls.validate)
        ])

    @classmethod
    def validate(cls, value: Any) -> Self:
        """
        Validate and convert input to an ApprovedUUID instance.
        """
        return cls(value)

    def __repr__(self) -> str:
        """
        Provide a clear representation of the UUID.
        """
        return f"ApprovedUUID('{self}')"

    def to_dict(self) -> dict:
        """
        Convert UUID to a dictionary representation.
        """
        return {"uuid": str(self)}

    def to_json(self) -> str:
        """
        Convert UUID to a JSON string.
        """
        return json.dumps(str(self))

    def __hash__(self) -> int:
        """
        Make the ApprovedUUID hashable.
        """
        return hash(str(self))

# Example usage model to demonstrate serialization
class ExampleModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: ApprovedUUID = Field(
        description="A unique identifier using ApprovedUUID"
    )
    name: str

# Demonstration of usage
def example_usage():
    # Create from various input types
    uuid1 = ApprovedUUID("123e4567-e89b-12d3-a456-426614174000")
    
    # Create from an existing UUID instance
    existing_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    uuid2 = ApprovedUUID(existing_uuid)
    
    # Create a model instance
    model = ExampleModel(
        id=uuid1, 
        name="Example"
    )
    
    # Serialization demonstrations
    print(str(model.id))  # String representation
    print(model.id.to_dict())  # Dictionary representation
    print(model.id.to_json())  # JSON representation
    
    # Pydantic JSON schema will work correctly
    print(model.model_dump())
    print(model.model_dump_json())

if __name__ == "__main__":
    example_usage()