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
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import your FastAPI app and other modules
from main import app

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
        instance.topic_path.return_value = "projects/test-project/topics/test-topic"
        future = MagicMock()
        future.result.return_value = str(uuid.uuid4())
        instance.publish.return_value = future
        yield instance


@pytest.fixture
def mock_pubsub_failure():
    """Mock failed Pub/Sub message publishing."""
    with patch('google.cloud.pubsub_v1.PublisherClient') as mock_publisher:
        instance = mock_publisher.return_value
        instance.topic_path.return_value = "projects/test-project/topics/test-topic"
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


# More test classes and methods can follow as in your original file
# ...

if __name__ == "__main__":
    pytest.main(["-xvs", "test_main_api.py"])