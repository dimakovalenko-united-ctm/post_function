from pydantic import BaseModel, Field, UUID4, field_validator
from typing import Optional, Union, List, Dict
from common.models.date_time_iso8601 import ApprovedDateTime as DateTime
from common.models.database_structure import AllAllowedQueryReturns
from common.models.approved_uuid import ApprovedUUID as UUID
import json

# Define the Metadata model for the "metadata" field
class HttpResponseMetaData(BaseModel):
    rows: int
    query: Optional[dict]                = Field(None, deprecated="Query Params")
    start_timestamp: Optional[DateTime]  = Field(..., deprecated="Processing start time")
    finish_timestamp: Optional[DateTime] = Field(..., deprecated="Processing finish time")
    

# Define the HttpResponses model
class HttpResponses(BaseModel):
    data: AllAllowedQueryReturns
    metadata: Optional[HttpResponseMetaData]


class AllowedGetResponseData(BaseModel):
    id: UUID                  = Field(..., description="ID of the record")        
    crypto_name: str           = Field(..., description="Human Readable name")   
    crypto_symbol: str         = Field(..., description="3 Character crypto currency symbol such as 'BTC'")
    fiat_currency: str         = Field(..., description="3 Character fiat currency such as 'USD'")
    open: float                = Field(..., description="Open")
    close: float               = Field(..., description="Close")
    high: float                = Field(..., description="High") 
    low: float                 = Field(..., description="Low")
    volume: float              = Field(..., description="Volume")
    timestamp: DateTime        = Field(..., description="ISO 8601 Formatted timestamp of the price")  


    @classmethod
    def from_dict(cls, dict: dict):
        return cls (
            id             = dict['id'],
            crypto_name    = dict['crypto_name'],
            crypto_symbol  = dict['crypto_symbol'],
            fiat_currency  = dict['fiat_currency'],
            open           = dict['open'],
            close          = dict['close'],
            high           = dict['high'],
            low            = dict['low'],
            volume         = dict['volume'],
            timestamp      = dict['timestamp'],
        )

class AllowedPostResponseData(BaseModel):
    id: UUID                                    = Field(..., description="ID of the record")    
    message_id: Optional[str]                    = Field(None, description="Message id of PubSub Entry")
    input_data: Optional[list[dict]] = Field(None, description="Data attempted to insert")
    error: Optional[str]                         = Field(None, description="Errors")

    @field_validator('input_data')
    @classmethod
    def validate_input_data_size(cls, value: Optional[List[Dict]]) -> Optional[List[Dict]]:
        if value is not None and len(value) > 10:
            raise ValueError("The 'input_data' list must not exceed 10 elements.")
        return value

class HttpSerializableResponse(BaseModel):
    data: list[AllowedPostResponseData]
    metadata: Optional[HttpResponseMetaData] = None

    def model_dump(self, **kwargs):
        return {
            'data': [item.model_dump() for item in self.data],
            'metadata': self.metadata.model_dump() if self.metadata else None
        }

    def to_json(self):
        return json.dumps(self.model_dump())

class APIHttpPostResponses(HttpSerializableResponse):
    pass

class APIHttpGetResponse(HttpSerializableResponse):
    data: list[AllowedPostResponseData]
    metadata: Optional[HttpResponseMetaData] = None

class SuccessResponse(APIHttpPostResponses, APIHttpGetResponse):
    status: str = "success"
    data: Union[list[AllowedPostResponseData], list[AllowedGetResponseData]]

class ErrorResponse(APIHttpPostResponses, APIHttpGetResponse):
    status: str = "error, no records created"
    data: Union[list[AllowedPostResponseData], list[AllowedGetResponseData]]

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_data

    @classmethod
    def validate_data(cls, value):
        # Add logic to determine which model to use based on the data structure
        if isinstance(value[0].get("input_data"), list):
            return [AllowedPostResponseData(**item) for item in value]
        else:
            return [AllowedGetResponseData(**item) for item in value]

class WarningResponse(APIHttpPostResponses, APIHttpGetResponse):
    status: str = "partial success, some records created"
