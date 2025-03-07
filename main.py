#!/usr/bin/env python
import uuid
import json
import os
from common.fastapi_app import create_fastapi_app
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from common.local_runner import run_local
from google.cloud import pubsub_v1
from common.models.http_response_model import HttpSerializableResponse, HttpResponseMetaData, SuccessResponse, WarningResponse, ErrorResponse
from common.models.http_query_params import PostData
from common.logging_utils import info, error, audit, warning, debug, exception
from typing import List

from datetime import timezone

from common.models.date_time_iso8601 import ApprovedDateTime as DateTime

# Initialize the FastAPI app and handler using the shared module
app, handler = create_fastapi_app(title="Get ALL Function")


PROJECT_ID = "dev-test-staging"
TOPIC_NAME = "pricing-service-injest-topic"


def clean_nulls_and_empties(input: dict):
    """
    Most agrivating fix for AVRO ever!!!!!!
    Super Strict enforcement, optional fields have to be explicitly Null
                {
                    "timestamp": "2025-03-04T11:53:58.020176+00:00",
                    "dividends": 0.0,
                    "stock_splits": 0.0,
                    "crypto_name": "Bitcoin",
                    "crypto_symbol": "BTC",
                    "fiat_currency": "USDT",
                    "source": "Binance",
                    "open": 88680.39,
                    "close": 84250.09,
                    "high": 89414.15,
                    "low": 82256.01,
                    "volume": 4898429925.6364765,
                    "ticker": "BTCUSDT",
                    "id": "a17853e0-90ab-4613-94a4-ac7b179f8315",
                    "insertion_timestamp": "2025-03-04T11:53:58.020176+00:00",
                    "is_deleted": false,
                    "metadata": ""
                }
    """            

    return_data = {}

    for key in input.keys():
        if input[key] is False:
            return_data[key] = 'false'
        elif input[key] is None:
            return_data[key] = 'null'
        else:
            return_data[key] = input[key]

    return_data = json.dumps(input, indent=2)
    return_data = return_data.replace('"null"', 'null') #Annoing, but null has to be 'noll' not '"null"'

    return return_data


def publish_message_to_pubsub(project_id, topic_id, message_data: dict):

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    
    

    try:
        json_string = clean_nulls_and_empties(message_data)
        message_json = json_string.encode("utf-8")

        # Publish the message
        future = publisher.publish(topic_path, message_json)
        message_id = future.result()  # Block until published
        debug(f"Published message ID: {message_id}")
        return message_id

    except Exception as e:
        exception(f"Error publishing message: {e}")
        raise e

@app.post("/prices", responses={
                            201: {"model": SuccessResponse, "description": "All records created successfully"},
                            207: {"model": WarningResponse, "description": "Partial success, some records created others failed. Check response for errors."},
                            202: {"model": ErrorResponse, "description": "No records written, check response for failures"}
                        }
        )
def create_crypto(data: List[PostData]):            

    try:
        success_records = []
        failed_records  = []

        for input_record in data:        
            debug(f"{data[0].model_dump_json()}")        
            record_id = uuid.uuid4() #generate the UUID that we will use for all records, as ID in the DB
            meta_data_start_time = DateTime.now(timezone.utc)

        # Prepare the complete record for PubSub, see my gribing about explicit schema validation above
            record = {
                **input_record.model_dump(exclude_none=False), #Explicitly add all falses and nulls
                "id": str(record_id),
                "insertion_timestamp": meta_data_start_time.isoformat(),
                "is_deleted": False
            } 

            debug(f"Full record to insert {record}")            
                        
            try:
                # Publish to Pub/Sub and get message ID                            
                pubsub_message_id = publish_message_to_pubsub(PROJECT_ID, TOPIC_NAME, record)       
                record_info = {"id": record["id"], "message_id": pubsub_message_id}
                debug(record_info)
                success_records.append(record_info)
            except Exception as internal_exception: 
                failure = {"id": record["id"], "error": str(internal_exception), "input_data": record}
                exception(f"Failed to write {failure} as: {internal_exception}")
                failed_records.append(failure)                

        metadata_finish_timestamp = DateTime.now()

        metadata = HttpResponseMetaData(
            rows             = len(success_records + failed_records),
            finish_timestamp = metadata_finish_timestamp,
            start_timestamp  = meta_data_start_time
        )

        if success_records and failed_records:            
            post_return  = WarningResponse(
                data     = (success_records + failed_records),
                metadata = metadata
            )
            warning("Operation succeeded with warnings: {post_return}")

            return JSONResponse(status_code = 207, content=post_return.model_dump())

        elif success_records and not failed_records:
            post_return = SuccessResponse(
                data     = success_records,
                metadata = metadata
            )
            info("Operation succeeded without errors: {post_return}")

            return JSONResponse(status_code = 201, content=post_return.model_dump())

        else:            
            post_return = ErrorResponse(
                data     = failed_records,
                metadata = metadata
            )
            warning("Operation succeeded with warnings: {post_return}")
            return JSONResponse(status_code = 202, content=post_return.model_dump())


    except Exception as e:
        exception(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")



if __name__ == "__main__":
    import os
    import sys
    os.environ["ENVIRONMENT"] = "local"

    # Check if the --debug flag is passed as a command-line argument
    debug_mode = "--debug" in sys.argv
    
    if debug_mode:
        # Pass import string for debug mode with auto-reload
        run_local("main:app", debug=debug_mode)
    else:
        # Pass app instance for normal mode
        run_local(app, debug=debug_mode)