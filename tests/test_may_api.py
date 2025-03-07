#!/usr/bin/env python

#!/usr/bin/env python
"""
Comprehensive test suite for the pricing service API.
Tests cover validation, edge cases, and security concerns.
"""

import pytest
import json
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta

from main import app  # Import your FastAPI app

# Create test client
client = TestClient(app)

# Constants
VALID_CRYPTO_PAYLOAD = [
    {
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
]

# Helper functions
def generate_iso_timestamp(days_ago=0):
    """Generate ISO 8601 timestamp for a given number of days ago."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


# Fixtures
@pytest.fixture
def mock_pubsub_success():
    """Mock successful Pub/Sub message publishing."""
    with patch('google.cloud.pubsub_v1.PublisherClient') as mock_publisher:
        instance = mock_publisher.return_value
        future = MagicMock()
        future.result.return_value = str(uuid.uuid4())
        instance.publish.return_value = future
        yield instance


@pytest.fixture
def mock_pubsub_failure():
    """Mock failed Pub/Sub message publishing."""
    with patch('google.cloud.pubsub_v1.PublisherClient') as mock_publisher:
        instance = mock_publisher.return_value
        instance.publish.side_effect = Exception("Pub/Sub error")
        yield instance


class TestValidationCases:
    """Test validation logic and error handling."""

    def test_valid_single_record(self, mock_pubsub_success):
        """Test submission of a single valid record."""
        response = client.post("/prices", json=VALID_CRYPTO_PAYLOAD)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == 1
        assert "id" in data["data"][0]
        assert "message_id" in data["data"][0]

    def test_valid_multiple_records(self, mock_pubsub_success):
        """Test submission of multiple valid records."""
        # Create multiple records
        multi_payload = [
            VALID_CRYPTO_PAYLOAD[0],
            {**VALID_CRYPTO_PAYLOAD[0], "crypto_name": "Ethereum", "crypto_symbol": "ETH"}
        ]
        
        response = client.post("/prices", json=multi_payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == 2

    def test_missing_required_field(self):
        """Test validation when a required field is missing."""
        # Remove required field
        invalid_payload = [{
            k: v for k, v in VALID_CRYPTO_PAYLOAD[0].items() if k != "crypto_name"
        }]
        
        response = client.post("/prices", json=invalid_payload)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any("crypto_name" in str(error["loc"]) for error in data["detail"])

    def test_empty_payload(self):
        """Test validation with an empty payload."""
        response = client.post("/prices", json=[])
        
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_non_array_payload(self):
        """Test validation with a non-array payload."""
        response = client.post("/prices", json=VALID_CRYPTO_PAYLOAD[0])
        
        assert response.status_code == 422
        assert "detail" in response.json()


class TestRequiredFields:
    """Test required fields validation."""

    @pytest.mark.parametrize("field", [
        "crypto_name", "crypto_symbol", "fiat_currency", "source", 
        "open", "close", "high", "low", "volume", "ticker", "timestamp"
    ])
    def test_missing_required_field(self, field):
        """Test that each required field is actually required."""
        # Create payload with missing field
        payload = [{
            k: v for k, v in VALID_CRYPTO_PAYLOAD[0].items() if k != field
        }]
        
        response = client.post("/prices", json=payload)
        
        assert response.status_code == 422
        data = response.json()
        assert any(field in str(error["loc"]) for error in data["detail"])


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_future_timestamp(self):
        """Test validation with future timestamp."""
        # Create payload with future timestamp
        future_payload = [
            {**VALID_CRYPTO_PAYLOAD[0], "timestamp": generate_iso_timestamp(-30)}  # 30 days in future
        ]
        
        response = client.post("/prices", json=future_payload)
        
        # The validation should fail because timestamps shouldn't be in the future
        assert response.status_code == 422
        data = response.json()
        assert any("timestamp" in str(error["loc"]) for error in data["detail"])

    def test_invalid_timestamp_format(self):
        """Test validation with invalid timestamp format."""
        # Create payload with invalid timestamp
        invalid_payload = [
            {**VALID_CRYPTO_PAYLOAD[0], "timestamp": "2025-02-31"}  # Invalid date
        ]
        
        response = client.post("/prices", json=invalid_payload)
        
        assert response.status_code == 422
        data = response.json()
        assert any("timestamp" in str(error["loc"]) for error in data["detail"])

    def test_extremely_large_values(self):
        """Test with extremely large numeric values."""
        # Create payload with large values
        large_payload = [
            {**VALID_CRYPTO_PAYLOAD[0], "volume": 1e20, "high": 1e15}
        ]
        
        response = client.post("/prices", json=large_payload)
        
        # This should succeed as there are no explicit upper limits
        assert response.status_code == 201

    def test_zero_and_negative_values(self):
        """Test with zero and negative values for numeric fields."""
        # Create payload with zero and negative values
        zero_neg_payload = [
            {**VALID_CRYPTO_PAYLOAD[0], "volume": 0, "low": -100}
        ]
        
        response = client.post("/prices", json=zero_neg_payload)
        
        # This should succeed as there are no explicit non-negative requirements
        assert response.status_code == 201

    def test_very_long_strings(self):
        """Test with very long string values."""
        # Create payload with long strings
        long_payload = [
            {**VALID_CRYPTO_PAYLOAD[0], "crypto_name": "X" * 10000}
        ]
        
        response = client.post("/prices", json=long_payload)
        
        # No explicit length limitations in schema, so this should succeed
        assert response.status_code == 201


class TestOptionalFields:
    """Test optional fields behavior."""

    def test_omit_optional_fields(self, mock_pubsub_success):
        """Test omitting all optional fields."""
        # Create minimal payload with only required fields
        minimal_payload = [{
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
        }]
        
        response = client.post("/prices", json=minimal_payload)
        
        assert response.status_code == 201

    def test_null_optional_fields(self, mock_pubsub_success):
        """Test setting optional fields to null."""
        # Create payload with null optional fields
        null_payload = [
            {**VALID_CRYPTO_PAYLOAD[0], "metadata": None, "dividends": None, "stock_splits": None}
        ]
        
        response = client.post("/prices", json=null_payload)
        
        # This should succeed as nulls are converted to defaults
        assert response.status_code == 201


class TestErrorHandling:
    """Test error handling and partial success scenarios."""

    def test_partial_success(self, mock_pubsub_success):
        """Test partial success with some valid and some invalid records."""
        with patch('main.publish_message_to_pubsub') as mock_publish:
            # Make the first record succeed, second fail
            mock_publish.side_effect = [str(uuid.uuid4()), Exception("Pub/Sub error")]
            
            multi_payload = [
                VALID_CRYPTO_PAYLOAD[0],
                {**VALID_CRYPTO_PAYLOAD[0], "crypto_name": "Ethereum", "crypto_symbol": "ETH"}
            ]
            
            response = client.post("/prices", json=multi_payload)
            
            assert response.status_code == 207  # Partial success
            data = response.json()
            assert data["status"] == "partial success, some records created"
            assert len(data["data"]) == 2
            assert any("error" in record and record["error"] for record in data["data"])

    def test_complete_failure(self, mock_pubsub_failure):
        """Test complete failure when all records fail to publish."""
        response = client.post("/prices", json=VALID_CRYPTO_PAYLOAD)
        
        assert response.status_code == 202  # Accepted but no records created
        data = response.json()
        assert data["status"] == "error, no records created"
        assert all("error" in record for record in data["data"])

    def test_server_error_handling(self):
        """Test server error handling with an unhandled exception."""
        with patch('main.create_crypto', side_effect=Exception("Unexpected error")):
            response = client.post("/prices", json=VALID_CRYPTO_PAYLOAD)
            
            assert response.status_code == 500
            assert "detail" in response.json()


class TestSecurityConcerns:
    """Test security-related concerns."""

    def test_sql_injection_attempt(self, mock_pubsub_success):
        """Test SQL injection attempt in string fields."""
        sql_payload = [
            {**VALID_CRYPTO_PAYLOAD[0], "crypto_name": "'; DROP TABLE users; --"}
        ]
        
        response = client.post("/prices", json=sql_payload)
        
        # This should succeed as we're not directly using SQL and Pub/Sub handles the message
        assert response.status_code == 201

    def test_xss_attempt(self, mock_pubsub_success):
        """Test cross-site scripting (XSS) attempt."""
        xss_payload = [
            {**VALID_CRYPTO_PAYLOAD[0], "crypto_name": "<script>alert('XSS')</script>"}
        ]
        
        response = client.post("/prices", json=xss_payload)
        
        # This should succeed as the API doesn't render HTML
        assert response.status_code == 201

    def test_metadata_json_injection(self, mock_pubsub_success):
        """Test JSON injection in metadata field."""
        # Create payload with malicious-looking JSON metadata
        metadata = json.dumps({
            "injected": True, 
            "__proto__": {"polluted": True},
            "constructor": {"prototype": {"isAdmin": True}}
        })
        
        injection_payload = [
            {**VALID_CRYPTO_PAYLOAD[0], "metadata": metadata}
        ]
        
        response = client.post("/prices", json=injection_payload)
        
        # This should succeed as the metadata is just stored as a string
        assert response.status_code == 201

    def test_extremely_nested_json(self):
        """Test with extremely deeply nested JSON structure."""
        # Create a deeply nested structure
        nested = {}
        current = nested
        for i in range(100):  # 100 levels of nesting
            current["nested"] = {}
            current = current["nested"]
        
        nested_payload = [
            {**VALID_CRYPTO_PAYLOAD[0], "metadata": json.dumps(nested)}
        ]
        
        response = client.post("/prices", json=nested_payload)
        
        # JSON parsing limits should handle this properly
        assert response.status_code in (201, 400, 413)  # Success or appropriate error


if __name__ == "__main__":
    pytest.main(["-xvs", "test_main_api.py"])