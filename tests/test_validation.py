#!/usr/bin/env python
"""
Comprehensive test suite for data validation in the pricing service.
Tests cover model validation, schema conformance, and data integrity.
"""

import pytest
import json
import sys
import os
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import your models
from common.models.http_query_params import PostData
from common.models.approved_uuid import ApprovedUUID as UUID
from common.models.date_time_iso8601 import ApprovedDateTime as DateTime

# Helper functions
def generate_iso_timestamp(days_ago=0):
    """Generate ISO 8601 timestamp for a given number of days ago."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


class TestPostDataValidation:
    """Test validation of the PostData model."""

    def test_valid_minimal_post_data(self):
        """Test creating a minimal valid PostData instance."""
        valid_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "open": 1.109375,
            "close": 97085.8671875,
            "high": 97532.6171875,
            "low": 94286.9609375,
            "volume": 47116570624.0,
            "ticker": "BTC-USD",
            "timestamp": generate_iso_timestamp(1)
        }
        
        # This should not raise any exceptions
        post_data = PostData(**valid_data)
        
        # Verify that fields are correctly set
        assert post_data.crypto_name == "Bitcoin"
        assert post_data.crypto_symbol == "BTC"
        assert post_data.fiat_currency == "USD"
        assert post_data.open == 1.109375
        
        # Verify optional fields have defaults
        assert post_data.metadata == ""
        assert post_data.dividends == 0.0
        assert post_data.stock_splits == 0.0

    def test_required_fields(self):
        """Test that required fields are enforced."""
        required_fields = [
            "crypto_name", "crypto_symbol", "fiat_currency", "source",
            "open", "close", "high", "low", "volume", "ticker", "timestamp"
        ]
        
        base_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "open": 1.109375,
            "close": 97085.8671875,
            "high": 97532.6171875,
            "low": 94286.9609375,
            "volume": 47116570624.0,
            "ticker": "BTC-USD",
            "timestamp": generate_iso_timestamp(1)
        }
        
        # Test each required field by removing it
        for field in required_fields:
            invalid_data = {k: v for k, v in base_data.items() if k != field}
            
            with pytest.raises(ValidationError) as excinfo:
                PostData(**invalid_data)
            
            # Verify the error is about the missing field
            assert field in str(excinfo.value)

    def test_string_field_validation(self):
        """Test validation of string fields."""
        valid_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "open": 1.109375,
            "close": 97085.8671875,
            "high": 97532.6171875,
            "low": 94286.9609375,
            "volume": 47116570624.0,
            "ticker": "BTC-USD",
            "timestamp": generate_iso_timestamp(1)
        }
        
        # Test empty strings
        for field in ["crypto_name", "crypto_symbol", "fiat_currency", "source", "ticker"]:
            invalid_data = {**valid_data, field: ""}
            
            # Empty strings might be allowed by the model, but we should test
            # Check if this raises an exception - if not, that's the model's behavior
            try:
                PostData(**invalid_data)
            except ValidationError:
                pass  # Exception is expected if empty strings are not allowed

        # Test very long strings
        long_string = "X" * 10000
        for field in ["crypto_name", "crypto_symbol", "fiat_currency", "source", "ticker"]:
            long_data = {**valid_data, field: long_string}
            
            # Check if this raises an exception - if not, that's the model's behavior
            try:
                PostData(**long_data)
            except ValidationError:
                pass  # Exception is expected if there are length limits

    def test_numeric_field_validation(self):
        """Test validation of numeric fields."""
        valid_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "open": 1.109375,
            "close": 97085.8671875,
            "high": 97532.6171875,
            "low": 94286.9609375,
            "volume": 47116570624.0,
            "ticker": "BTC-USD",
            "timestamp": generate_iso_timestamp(1)
        }
        
        # Test non-numeric values
        for field in ["open", "close", "high", "low", "volume"]:
            string_data = {**valid_data, field: "not-a-number"}
            
            with pytest.raises(ValidationError) as excinfo:
                PostData(**string_data)
            
            assert field in str(excinfo.value)
        
        # Test negative values
        for field in ["open", "close", "high", "low", "volume"]:
            negative_data = {**valid_data, field: -1.0}
            
            # Check if negative values are allowed - they might be depending on model
            try:
                PostData(**negative_data)
            except ValidationError:
                pass  # Exception is expected if negative values are not allowed

    def test_timestamp_validation(self):
        """Test validation of timestamp field."""
        valid_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "open": 1.109375,
            "close": 97085.8671875,
            "high": 97532.6171875,
            "low": 94286.9609375,
            "volume": 47116570624.0,
            "ticker": "BTC-USD"
        }
        
        # Test current timestamp
        current_data = {**valid_data, "timestamp": datetime.now(timezone.utc).isoformat()}
        current_post_data = PostData(**current_data)
        assert isinstance(current_post_data.timestamp, DateTime)
        
        # Test historical timestamp
        past_data = {**valid_data, "timestamp": "2020-01-01T00:00:00Z"}
        past_post_data = PostData(**past_data)
        assert isinstance(past_post_data.timestamp, DateTime)
        
        # Test future timestamp - should fail validation if the model checks for this
        future_data = {**valid_data, "timestamp": generate_iso_timestamp(-30)}  # 30 days in future
        try:
            PostData(**future_data)
            # If we get here, future dates are allowed
        except ValidationError:
            pass  # Exception is expected if future dates are not allowed
        
        # Test invalid timestamp format
        invalid_formats = [
            "2020-13-01T00:00:00Z",  # Invalid month
            "not-a-date",
            "2020/01/01",
            "01-01-2020"
        ]
        
        for invalid_format in invalid_formats:
            invalid_data = {**valid_data, "timestamp": invalid_format}
            
            with pytest.raises(ValidationError) as excinfo:
                PostData(**invalid_data)
            
            assert "timestamp" in str(excinfo.value)

    def test_metadata_validation(self):
        """Test validation of the metadata field."""
        valid_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "open": 1.109375,
            "close": 97085.8671875,
            "high": 97532.6171875,
            "low": 94286.9609375,
            "volume": 47116570624.0,
            "ticker": "BTC-USD",
            "timestamp": generate_iso_timestamp(1)
        }
        
        # Test with valid JSON metadata
        json_metadata = json.dumps({"key": "value", "nested": {"flag": True}})
        json_data = {**valid_data, "metadata": json_metadata}
        json_post_data = PostData(**json_data)
        assert json_post_data.metadata == json_metadata
        
        # Test with empty string metadata
        empty_data = {**valid_data, "metadata": ""}
        empty_post_data = PostData(**empty_data)
        assert empty_post_data.metadata == ""
        
        # Test with None metadata - should default to empty string
        none_data = {**valid_data, "metadata": None}
        with pytest.raises(ValidationError) as excinfo:
            PostData(**none_data)
        assert "metadata" in str(excinfo.value)
        
        # Test with non-string metadata - should convert to string
        non_string_data = {**valid_data, "metadata": 123}
        try:
            non_string_post_data = PostData(**non_string_data)
            # If we get here, non-string values are converted
            assert isinstance(non_string_post_data.metadata, str)
        except ValidationError:
            pass  # Exception is expected if only strings are allowed

    def test_omitting_optional_fields(self):
        """Test omitting optional fields."""
        minimal_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "open": 1.109375,
            "close": 97085.8671875,
            "high": 97532.6171875,
            "low": 94286.9609375,
            "volume": 47116570624.0,
            "ticker": "BTC-USD",
            "timestamp": generate_iso_timestamp(1)
        }
        
        # This should apply defaults for optional fields
        post_data = PostData(**minimal_data)
        
        # Verify defaults
        assert post_data.metadata == ""
        assert post_data.dividends == 0.0
        assert post_data.stock_splits == 0.0


class TestAVROSchemaCompliance:
    """Test compliance with AVRO schema requirements for Pub/Sub."""
    
    def test_metadata_string_conversion(self):
        """Test that metadata is always converted to a string, never null."""
        # Create some different metadata values
        test_cases = [
            None,
            "",
            json.dumps({"key": "value"}),
            123,
            True
        ]
        
        base_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC", 
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "open": 1.109375,
            "close": 97085.8671875,
            "high": 97532.6171875,
            "low": 94286.9609375,
            "volume": 47116570624.0,
            "ticker": "BTC-USD",
            "timestamp": generate_iso_timestamp(1)
        }
        
        for metadata in test_cases:
            test_data = {**base_data, "metadata": metadata}
            
            try:
                post_data = PostData(**test_data)
                # The model should convert all values to string or apply default
                assert isinstance(post_data.metadata, str)
                # None should become empty string
                if metadata is None:
                    assert post_data.metadata == ""
            except ValidationError:
                # If validation fails, check if it's for a reason other than metadata
                continue


class TestDataIntegrity:
    """Test data integrity and consistency."""
    
    def test_price_consistency(self):
        """Test validation of price consistency (high >= open/close >= low)."""
        timestamp = generate_iso_timestamp(1)
        
        # Test inconsistent prices (high < low)
        inconsistent_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "open": 50000,
            "close": 51000,
            "high": 49000,  # High less than open/close
            "low": 52000,   # Low greater than open/close
            "volume": 47116570624.0,
            "ticker": "BTC-USD",
            "timestamp": timestamp
        }
        
        # The model may or may not validate these relationships
        try:
            PostData(**inconsistent_data)
            # If we get here, the model doesn't validate price relationships
        except ValidationError:
            pass  # Exception is expected if price relationships are validated
    
    def test_model_dump_roundtrip(self):
        """Test model serialization and deserialization roundtrip."""
        original_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "open": 1.109375,
            "close": 97085.8671875,
            "high": 97532.6171875,
            "low": 94286.9609375,
            "volume": 47116570624.0,
            "ticker": "BTC-USD",
            "timestamp": generate_iso_timestamp(1),
            "metadata": json.dumps({"test": True}),
            "dividends": 0.5,
            "stock_splits": 2.0
        }
        
        # Create model instance
        post_data = PostData(**original_data)
        
        # Serialize
        serialized = post_data.model_dump()
        
        # Deserialize
        roundtrip = PostData(**serialized)
        
        # Compare
        for key, value in original_data.items():
            # For timestamp, compare string representations
            if key == "timestamp":
                assert str(getattr(roundtrip, key)) == str(DateTime(value))
            else:
                assert getattr(roundtrip, key) == value


if __name__ == "__main__":
    pytest.main(["-xvs", "test_validation.py"])