#!/usr/bin/env python
#!/usr/bin/env python
"""
Test suite for AVRO schema validation in the pricing service.
Tests verify that messages conform to the AVRO schema requirements.
"""

import pytest
import json
import uuid
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

# Import necessary modules
from main import clean_nulls_and_empties

# Helper functions
def generate_iso_timestamp(days_ago=0):
    """Generate ISO 8601 timestamp for a given number of days ago."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


class TestAVROSchemaValidation:
    """Test the conformance of messages to the AVRO schema."""

    def setup_method(self):
        """Setup the test by loading the AVRO schema."""
        # Load the AVRO schema from file
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'avro_schema.avsc')
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
        
        # Create a valid test record with all required fields
        self.valid_record = {
            "id": str(uuid.uuid4()),
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "test-source",
            "open": 50000.0,
            "close": 51000.0,
            "high": 52000.0, 
            "low": 49000.0,
            "volume": 1000.0,
            "ticker": "BTC-USD",
            "dividends": 0.0,
            "stock_splits": 0.0,
            "metadata": "",
            "timestamp": "2023-01-01T00:00:00Z",
            "insertion_timestamp": "2023-01-01T00:00:00Z",
            "is_deleted": False
        }

    def test_schema_required_fields(self):
        """Test that all required fields in the schema are present in our record."""
        # Extract required fields from schema
        required_fields = []
        for field in self.schema["fields"]:
            if "default" not in field:
                required_fields.append(field["name"])
        
        # Verify all required fields are in our test record
        for field in required_fields:
            assert field in self.valid_record, f"Required field '{field}' missing from test record"

    def test_schema_field_types(self):
        """Test that field types match the schema definitions."""
        # Create a map of field types from schema
        field_types = {}
        for field in self.schema["fields"]:
            if isinstance(field["type"], dict):
                field_types[field["name"]] = field["type"]["type"]
            else:
                field_types[field["name"]] = field["type"]
        
        # Prepare record for validation by cleaning nulls
        json_str = clean_nulls_and_empties(self.valid_record)
        cleaned_record = json.loads(json_str)
        
        # Validate field types
        for field, expected_type in field_types.items():
            if field in cleaned_record:
                if expected_type == "float":
                    assert isinstance(cleaned_record[field], (int, float)), f"Field '{field}' should be a number"
                elif expected_type == "string":
                    assert isinstance(cleaned_record[field], str), f"Field '{field}' should be a string"
                elif expected_type == "boolean":
                    # Handle both boolean and string representation of boolean
                    value = cleaned_record[field]
                    is_valid = isinstance(value, bool) or (isinstance(value, str) and value.lower() in ("true", "false"))
                    assert is_valid, f"Field '{field}' should be a boolean or string representation of boolean"

    def test_metadata_never_null(self):
        """Test that metadata is never null in the cleaned record."""
        # Test with null metadata
        test_record = self.valid_record.copy()
        test_record["metadata"] = None
        
        # Clean nulls and empties
        json_str = clean_nulls_and_empties(test_record)
        cleaned_record = json.loads(json_str)
        
        # Verify metadata is not null
        assert cleaned_record["metadata"] != None
        assert cleaned_record["metadata"] == ""

    def test_boolean_representation(self):
        """Test that boolean fields are represented correctly for AVRO."""
        # Test with boolean field
        test_record = self.valid_record.copy()
        test_record["is_deleted"] = False
        
        # Clean nulls and empties
        json_str = clean_nulls_and_empties(test_record)
        cleaned_record = json.loads(json_str)
        
        # Check how boolean is represented
        # This test verifies the expected behavior, which might be a boolean
        # or a string representation depending on your implementation
        assert cleaned_record["is_deleted"] is False or cleaned_record["is_deleted"] == "false"

    @patch('google.cloud.pubsub_v1.PublisherClient')
    def test_successful_schema_validation(self, mock_publisher_class):
        """
        Test that a well-formed message passes schema validation.
        
        Note: This test mocks the actual call to Pub/Sub. In a real environment,
        schema validation happens server-side in Pub/Sub.
        """
        # Setup mock
        mock_publisher = mock_publisher_class.return_value
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"
        
        mock_future = MagicMock()
        mock_future.result.return_value = "test-message-id"
        mock_publisher.publish.return_value = mock_future
        
        from main import publish_message_to_pubsub
        
        # Call the function with a well-formed record
        result = publish_message_to_pubsub("test-project", "test-topic", self.valid_record)
        
        # Verify the call succeeded
        assert result == "test-message-id"
        mock_publisher.publish.assert_called_once()


class TestEdgeCases:
    """Test edge cases for AVRO schema validation."""

    def test_empty_ticker(self):
        """Test with empty ticker string."""
        test_record = {
            "id": str(uuid.uuid4()),
            "crypto_name": "Bitcoin", 
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "test",
            "open": 50000.0,
            "close": 51000.0,
            "high": 52000.0,
            "low": 49000.0,
            "volume": 1000.0,
            "ticker": "",  # Empty ticker
            "timestamp": "2023-01-01T00:00:00Z",
            "insertion_timestamp": "2023-01-01T00:00:00Z",
            "is_deleted": False,
            "metadata": ""
        }
        
        # Clean nulls and empties
        json_str = clean_nulls_and_empties(test_record)
        cleaned_record = json.loads(json_str)
        
        # Empty string for ticker should be preserved as is
        assert cleaned_record["ticker"] == ""

    def test_large_numbers(self):
        """Test with large numeric values."""
        test_record = {
            "id": str(uuid.uuid4()),
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "test", 
            "open": 1e20,  # Very large number
            "close": 1e20,
            "high": 1e20,
            "low": 1e20,
            "volume": 1e20,
            "ticker": "BTC-USD",
            "timestamp": "2023-01-01T00:00:00Z",
            "insertion_timestamp": "2023-01-01T00:00:00Z",
            "is_deleted": False,
            "metadata": ""
        }
        
        # Clean nulls and empties
        json_str = clean_nulls_and_empties(test_record)
        cleaned_record = json.loads(json_str)
        
        # Large numbers should be preserved
        assert cleaned_record["open"] == 1e20
        assert cleaned_record["volume"] == 1e20

    def test_special_characters(self):
        """Test with special characters in string fields."""
        test_record = {
            "id": str(uuid.uuid4()),
            "crypto_name": "Bitcoin\u00A9™",  # With copyright and trademark symbols
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "test-source\n\r\t",  # With escape characters
            "open": 50000.0,
            "close": 51000.0,
            "high": 52000.0,
            "low": 49000.0,
            "volume": 1000.0,
            "ticker": "BTC-USD",
            "timestamp": "2023-01-01T00:00:00Z",
            "insertion_timestamp": "2023-01-01T00:00:00Z",
            "is_deleted": False,
            "metadata": "<script>alert('XSS')</script>"  # With HTML/script tags
        }
        
        # Clean nulls and empties
        json_str = clean_nulls_and_empties(test_record)
        cleaned_record = json.loads(json_str)
        
        # Special characters should be preserved
        assert cleaned_record["crypto_name"] == "Bitcoin\u00A9™"
        assert cleaned_record["source"] == "test-source\n\r\t"
        assert cleaned_record["metadata"] == "<script>alert('XSS')</script>"


if __name__ == "__main__":
    pytest.main(["-xvs", "test_avro_schema.py"])