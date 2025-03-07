#!/usr/bin/env python
import uuid
import json
import os
from common.fastapi_app import create_fastapi_app
from fastapi import HTTPException, Body
from fastapi.responses import JSONResponse
from common.local_runner import run_local
from google.cloud import pubsub_v1
from common.models.http_response_model import HttpSerializableResponse, HttpResponseMetaData, SuccessResponse, WarningResponse, ErrorResponse
from common.models.http_query_params import PostData
from common.logging_utils import info, error, audit, warning, debug, exception
from typing import List
from pydantic import validator


from datetime import timezone

from common.models.date_time_iso8601 import ApprovedDateTime as DateTime

# Initialize the FastAPI app and handler using the shared module
app, handler = create_fastapi_app(title="Get ALL Function")


PROJECT_ID = "dev-test-staging"
TOPIC_NAME = "pricing-service-injest-topic"


def clean_nulls_and_empties(input: dict):
    """
    Clean and prepare data for AVRO schema validation.
    
    AVRO has strict enforcement - optional fields have to be explicitly 
    handled correctly, especially for nulls and empty strings.
    """            
    return_data = {}

    for key, value in input.items():
        if value is False:
            return_data[key] = False
        elif value is None:
            # For metadata specifically, use empty string instead of null
            if key == "metadata":
                return_data[key] = ""
            else:
                return_data[key] = None
        else:
            return_data[key] = value

    # Convert to JSON string
    json_data = json.dumps(return_data)
    
    # In AVRO, null must be actual null not "null" string
    return json_data


def publish_message_to_pubsub(project_id, topic_id, message_data: dict):
    """
    Publish a message to Google Cloud Pub/Sub.
    
    Args:
        project_id: Google Cloud project ID
        topic_id: Pub/Sub topic ID
        message_data: Dictionary containing the message data
        
    Returns:
        The published message ID
        
    Raises:
        Exception: If message publishing fails
    """
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    
    try:
        # Ensure metadata is never null to match schema requirements
        if "metadata" not in message_data or message_data["metadata"] is None:
            message_data["metadata"] = ""
            
        json_string = clean_nulls_and_empties(message_data)
        message_json = json_string.encode("utf-8")

        # Publish the message
        future = publisher.publish(topic_path, message_json)
        message_id = future.result()  # Block until published
        debug(f"Published message ID: {message_id}")
        return message_id

    except Exception as e:
        exception(f"Error publishing message: {e}")
        raise e  # Make sure to re-raise the exception

@app.post("/prices", responses={
                          201: {"model": SuccessResponse, "description": "All records created successfully"},
                          207: {"model": WarningResponse, "description": "Partial success, some records created others failed. Check response for errors."},
                          202: {"model": ErrorResponse, "description": "No records written, check response for failures"}
                      }
      )
def create_crypto(data: List[PostData] = Body(..., min_items=1)):
    """
    Create new cryptocurrency price records via Pub/Sub.
    """
    
    if not data:
        raise HTTPException(status_code=422, detail="Request body cannot be empty")

    try:
        success_records = []
        failed_records  = []

        for input_record in data:        
            debug(f"Processing record: {input_record.model_dump_json()}")        
            record_id = uuid.uuid4()  # Generate UUID for DB record

            meta_data_start_time = DateTime.now(timezone.utc)

            # Prepare the complete record for PubSub
            record = {
                **input_record.model_dump(exclude_none=False),  # Include all fields
                "id": str(record_id),
                "insertion_timestamp": meta_data_start_time.isoformat(),
                "is_deleted": False
            } 
            
            # Ensure metadata is never null
            if "metadata" not in record or record["metadata"] is None:
                record["metadata"] = ""

            debug(f"Full record to insert: {record}")            
                        
            try:
                # Publish to Pub/Sub and get message ID                            
                pubsub_message_id = publish_message_to_pubsub(PROJECT_ID, TOPIC_NAME, record)       
                record_info = {"id": record["id"], "message_id": pubsub_message_id}
                debug(f"Successfully published record: {record_info}")
                success_records.append(record_info)
            except Exception as internal_exception: 
                # Create a failure record with the correct structure for your model
                failure = {
                    "id": record["id"], 
                    "error": str(internal_exception), 
                    "input_data": None  # Or format it correctly as expected by your model
                }
                exception(f"Failed to write record: {failure}")
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
            warning(f"Operation succeeded with warnings: {post_return}")
            return JSONResponse(status_code = 207, content=post_return.model_dump())

        elif success_records and not failed_records:
            post_return = SuccessResponse(
                data     = success_records,
                metadata = metadata
            )
            info(f"Operation succeeded without errors: {post_return}")
            return JSONResponse(status_code = 201, content=post_return.model_dump())

        else:            
            try:
                # Make sure your ErrorResponse is correctly structured
                post_return = ErrorResponse(
                    data     = failed_records,
                    metadata = metadata
                )
                error(f"Operation failed: {post_return}")
                return JSONResponse(status_code = 202, content=post_return.model_dump())
            except Exception as e:
                # Catch any validation errors in the response creation
                exception(f"Error creating error response: {e}")
                # Create a simpler error response that won't fail validation
                return JSONResponse(
                    status_code = 202, 
                    content = {
                        "status": "error, no records created",
                        "data": [{"id": record_id, "error": "Processing error"}],
                        "metadata": {"rows": len(failed_records)}
                    }
                )

    except Exception as e:
        exception(f"Unhandled exception: {e}")
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