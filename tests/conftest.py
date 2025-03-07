#!/usr/bin/env python
"""
Configuration file for pytest.
Provides shared fixtures for testing the pricing service.
"""

import pytest
import os
import sys
import json
import uuid
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import the main app
from main import app

@pytest.fixture(scope="session")
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def valid_crypto_payload():
    """Return a valid crypto price payload for testing."""
    return [
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
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    ]

@pytest.fixture
def valid_crypto_payload_with_metadata():
    """Return a valid crypto price payload with metadata for testing."""
    return [
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": json.dumps({"source_details": {"reliability": "high"}, "tags": ["popular", "volatile"]}),
            "dividends": 0.0,
            "stock_splits": 0.0
        }
    ]

@pytest.fixture
def minimal_crypto_payload():
    """Return a minimal crypto price payload with only required fields."""
    return [
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
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    ]

@pytest.fixture
def multi_crypto_payload():
    """Return a payload with multiple crypto price records."""
    current_time = datetime.now(timezone.utc).isoformat()
    return [
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
            "timestamp": current_time
        },
        {
            "open": 2200.50,
            "crypto_name": "Ethereum",
            "crypto_symbol": "ETH",
            "ticker": "ETH-USD",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "close": 2250.75,
            "high": 2300.00,
            "low": 2150.25,
            "volume": 15234567890.0,
            "timestamp": current_time
        },
        {
            "open": 0.85,
            "crypto_name": "Cardano",
            "crypto_symbol": "ADA",
            "ticker": "ADA-USD",
            "fiat_currency": "USD",
            "source": "yahoo-finance",
            "close": 0.87,
            "high": 0.89,
            "low": 0.83,
            "volume": 2345678901.0,
            "timestamp": current_time
        }
    ]

@pytest.fixture
def invalid_crypto_payload():
    """Return an invalid crypto price payload missing required fields."""
    return [
        {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            # Missing many required fields
            "high": 97532.6171875,
            "low": 94286.9609375
        }
    ]

@pytest.fixture
def mock_pubsub_success():
    """Mock successful Pub/Sub message publishing."""
    with patch('google.cloud.pubsub_v1.PublisherClient') as mock_publisher:
        instance = mock_publisher.return_value
        instance.topic_path.return_value = "projects/test-project/topics/test-topic"
        
        mock_future = MagicMock()
        mock_future.result.return_value = str(uuid.uuid4())
        instance.publish.return_value = mock_future
        
        yield instance

@pytest.fixture
def mock_pubsub_failure():
    """Mock failed Pub/Sub message publishing."""
    with patch('google.cloud.pubsub_v1.PublisherClient') as mock_publisher:
        instance = mock_publisher.return_value
        instance.topic_path.return_value = "projects/test-project/topics/test-topic"
        instance.publish.side_effect = Exception("Pub/Sub error")
        
        yield instance

@pytest.fixture
def mock_pubsub_partial_failure():
    """Mock Pub/Sub with some successes and some failures."""
    with patch('google.cloud.pubsub_v1.PublisherClient') as mock_publisher:
        instance = mock_publisher.return_value
        instance.topic_path.return_value = "projects/test-project/topics/test-topic"
        
        # Setup for tracking calls
        call_counter = [0]  # Use a list so we can modify it inside the closure
        
        # First call succeeds, second fails
        mock_future = MagicMock()
        mock_future.result.return_value = str(uuid.uuid4())
        
        def side_effect(*args, **kwargs):
            call_counter[0] += 1
            if call_counter[0] == 1:
                return mock_future
            else:
                raise Exception("Pub/Sub error on second record")
        
        instance.publish.side_effect = side_effect
        
        yield instance