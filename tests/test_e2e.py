#!/usr/bin/env python
"""
End-to-end tests for the pricing service.
Tests the entire flow from API request to Pub/Sub message.
"""

import pytest
import json
import uuid
import unittest
from unittest.mock import patch, MagicMock, call
from fastapi.testclient import TestClient

# Import necessary modules
from main import app, PROJECT_ID, TOPIC_NAME


class TestEndToEndFlow:
    """Test the entire flow from API request to Pub/Sub message."""
    
    def test_successful_post(self, test_client, valid_crypto_payload, mock_pubsub_success):
        """Test a successful POST request end-to-end."""
        # Make the request
        response = test_client.post("/prices", json=valid_crypto_payload)
        
        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == 1
        assert "id" in data["data"][0]
        assert "message_id" in data["data"][0]
        
        # Verify Pub/Sub was called correctly
        mock_pubsub_success.topic_path.assert_called_once_with(PROJECT_ID, TOPIC_NAME)
        mock_pubsub_success.publish.assert_called_once()
        
        # Verify content of published message
        call_args = mock_pubsub_success.publish.call_args
        assert call_args is not None
        
        published_data = json.loads(call_args[0][1].decode('utf-8'))
        assert published_data["crypto_name"] == valid_crypto_payload[0]["crypto_name"]
        assert published_data["crypto_symbol"] == valid_crypto_payload[0]["crypto_symbol"]
        assert "metadata" in published_data
        assert "id" in published_data
        assert "insertion_timestamp" in published_data
        assert published_data["is_deleted"] is False

    def test_multiple_records(self, test_client, multi_crypto_payload, mock_pubsub_success):
        """Test posting multiple crypto records in a single request."""
        # Make the request
        response = test_client.post("/prices", json=multi_crypto_payload)
        
        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == len(multi_crypto_payload)
        
        # Each record should have an ID and message ID
        for record in data["data"]:
            assert "id" in record
            assert "message_id" in record
        
        # Verify Pub/Sub was called correctly - once for each record
        assert mock_pubsub_success.topic_path.call_count == len(multi_crypto_payload)
        assert mock_pubsub_success.publish.call_count == len(multi_crypto_payload)
        
        # Verify the content of published messages
        call_args_list = mock_pubsub_success.publish.call_args_list
        assert len(call_args_list) == len(multi_crypto_payload)
        
        # Check each published message contains the correct data
        for i, call_args in enumerate(call_args_list):
            published_data = json.loads(call_args[0][1].decode('utf-8'))
            assert published_data["crypto_name"] == multi_crypto_payload[i]["crypto_name"]
            assert published_data["crypto_symbol"] == multi_crypto_payload[i]["crypto_symbol"]
            assert "metadata" in published_data
            assert "id" in published_data
            assert "insertion_timestamp" in published_data

    def test_failed_post_on_pub_sub_level(self, test_client, valid_crypto_payload, mock_pubsub_failure):
        """Test a POST request that fails at the Pub/Sub level."""
        # Make the request
        response = test_client.post("/prices", json=valid_crypto_payload)

        # Verify response indicates failure
        assert response.status_code == 202  # Accepted but processing failed
        data = response.json()
        assert data["status"] == "error, no records created"
        assert len(data["data"]) == 1
        assert "error" in data["data"][0]
        assert "Pub/Sub error" in data["data"][0]["error"]
        
        # Verify Pub/Sub was called
        mock_pubsub_failure.topic_path.assert_called_once_with(PROJECT_ID, TOPIC_NAME)
        mock_pubsub_failure.publish.assert_called_once()

    def test_partial_success(self, test_client, multi_crypto_payload, mock_pubsub_partial_failure):
        """Test a POST request with partial success (some records succeed, some fail)."""
        # Use only the first two records for this test
        test_payload = multi_crypto_payload[:2]
        
        # Make the request
        response = test_client.post("/prices", json=test_payload)
        
        # Verify response indicates partial success
        assert response.status_code == 207  # Multi-status
        data = response.json()
        assert data["status"] == "partial success, some records created"
        assert len(data["data"]) == 2
        
        # First record should have succeeded
        assert "message_id" in data["data"][0]
        assert data["data"][0]["error"] is None  # Changed this line from "error" not in data["data"][0]
        
        # Second record should have failed
        assert "error" in data["data"][1]
        assert "Pub/Sub error on second record" in data["data"][1]["error"]
        
        # Verify Pub/Sub was called twice
        assert mock_pubsub_partial_failure.topic_path.call_count == 2
        assert mock_pubsub_partial_failure.publish.call_count == 2

    def test_validation_failure(self, test_client, invalid_crypto_payload):
        """Test a POST request that fails validation."""
        # Make the request
        response = test_client.post("/prices", json=invalid_crypto_payload)
        
        # Verify response indicates validation failure
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data
        
        # Verify no Pub/Sub calls were made
        # No need to mock Pub/Sub here as validation happens before publishing

    @patch('main.publish_message_to_pubsub')
    def test_metadata_handling(self, mock_publish, test_client, valid_crypto_payload_with_metadata):
        """Test that metadata is properly handled in the end-to-end flow."""
        # Setup the mock
        mock_publish.return_value = "test-message-id"
        
        # Make the request
        response = test_client.post("/prices", json=valid_crypto_payload_with_metadata)
        
        # Verify response
        assert response.status_code == 201
        
        # Check that metadata was passed correctly
        call_args = mock_publish.call_args
        assert call_args is not None
        
        # Get the message data that was passed to publish_message_to_pubsub
        message_data = call_args[0][2]
        assert "metadata" in message_data
        assert message_data["metadata"] == valid_crypto_payload_with_metadata[0]["metadata"]

    @patch('main.publish_message_to_pubsub')
    def test_missing_optional_fields(self, mock_publish, test_client, minimal_crypto_payload):
        """Test that missing optional fields are handled correctly."""
        # Setup the mock
        mock_publish.return_value = "test-message-id"
        
        # Make the request
        response = test_client.post("/prices", json=minimal_crypto_payload)
        
        # Verify response
        assert response.status_code == 201
        
        # Check that optional fields were defaulted
        call_args = mock_publish.call_args
        assert call_args is not None
        
        # Get the message data that was passed to publish_message_to_pubsub
        message_data = call_args[0][2]
        
        # Metadata should default to empty string
        assert "metadata" in message_data
        assert message_data["metadata"] == ""
        
        # Dividends and stock_splits should default to 0.0
        assert "dividends" in message_data
        assert message_data["dividends"] == 0.0
        assert "stock_splits" in message_data
        assert message_data["stock_splits"] == 0.0

    @patch('uuid.uuid4')
    @patch('main.publish_message_to_pubsub')
    def test_id_generation(self, mock_publish, mock_uuid, test_client, valid_crypto_payload):
        """Test that UUIDs are correctly generated and included in messages."""
        # Setup the mocks
        test_uuid = "00000000-0000-0000-0000-000000000000"
        mock_uuid.return_value = uuid.UUID(test_uuid)
        mock_publish.return_value = "test-message-id"
        
        # Make the request
        response = test_client.post("/prices", json=valid_crypto_payload)
        
        # Verify response contains the UUID
        assert response.status_code == 201
        data = response.json()
        assert data["data"][0]["id"] == test_uuid
        
        # Check that the UUID was included in the published message
        call_args = mock_publish.call_args
        assert call_args is not None
        
        message_data = call_args[0][2]
        assert "id" in message_data
        assert message_data["id"] == test_uuid


class TestErrorHandling:
    """Test error handling in the API."""
    
    def test_pubsub_error_handling(self, test_client, valid_crypto_payload):
        """Test that Pub/Sub errors are handled gracefully."""
        
        # Patch the publish function to simulate a Pub/Sub error
        with unittest.mock.patch('main.publish_message_to_pubsub', 
                            side_effect=Exception("Unexpected server error")):
            # Make the request
            response = test_client.post("/prices", json=valid_crypto_payload)
            
            # Verify response indicates handled failure (202)
            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "error, no records created"
            assert len(data["data"]) == 1
            assert "error" in data["data"][0]
            assert "Unexpected server error" in data["data"][0]["error"]

    def test_empty_payload(self, test_client):
        """Test handling of an empty payload."""
        # Make the request with empty list
        response = test_client.post("/prices", json=[])
        
        # Verify response indicates validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        
        # Make the request with empty object
        response = test_client.post("/prices", json={})
        
        # Verify response indicates validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_invalid_json(self, test_client):
        """Test handling of invalid JSON in the request."""
        # Make the request with invalid JSON
        response = test_client.post("/prices", data="not valid json")
        
        # Verify response indicates bad request
        assert response.status_code in (400, 422)  # Either is acceptable
        assert "detail" in response.json()

    def test_method_not_allowed(self, test_client):
        """Test handling of unsupported HTTP methods."""
        # Try PUT request (should not be allowed)
        response = test_client.put("/prices", json={"test": True})
        
        # Verify response indicates method not allowed
        assert response.status_code == 405
        
        # Try DELETE request (should not be allowed)
        response = test_client.delete("/prices")
        
        # Verify response indicates method not allowed
        assert response.status_code == 405


class TestPerformance:
    """Basic performance tests for the API."""

    @patch('main.publish_message_to_pubsub')
    def test_large_batch(self, mock_publish, test_client):
        """Test handling of a large batch of records."""
        # Setup the mock
        mock_publish.return_value = "test-message-id"
        
        # Create a large batch of records (50 items)
        base_record = {
            "open": 1.109375,
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "ticker": "BTC-USD",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "close": 97085.8671875,
            "high": 97532.6171875,
            "low": 94286.9609375,
            "volume": 47116570624.0,
            "timestamp": "2025-02-01T16:13:56.604630+00:00"
        }
        
        large_batch = [base_record.copy() for _ in range(50)]
        
        # Make the request
        response = test_client.post("/prices", json=large_batch)
        
        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == 50
        
        # Verify all publish calls were made
        assert mock_publish.call_count == 50


class TestContentNegotiation:
    """Test content negotiation aspects of the API."""

    def test_content_type_requirements(self, test_client, valid_crypto_payload):
        """Test content type requirements for requests."""
        # Test with correct content type
        response = test_client.post(
            "/prices",
            json=valid_crypto_payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in (201, 202, 207)  # Any successful status is fine
        
        # Test with incorrect content type
        response = test_client.post(
            "/prices",
            data=json.dumps(valid_crypto_payload),
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code in (400, 415, 422)  # Either is acceptable

    def test_accept_header(self, test_client, valid_crypto_payload, mock_pubsub_success):
        """Test different Accept headers for responses."""
        # Test with JSON Accept header
        response = test_client.post(
            "/prices",
            json=valid_crypto_payload,
            headers={"Accept": "application/json"}
        )
        assert response.status_code == 201
        assert response.headers["Content-Type"] == "application/json"
        
        # Test with any Accept header
        response = test_client.post(
            "/prices",
            json=valid_crypto_payload,
            headers={"Accept": "*/*"}
        )
        assert response.status_code == 201
        assert "Content-Type" in response.headers


if __name__ == "__main__":
    pytest.main(["-xvs", "test_e2e.py"])