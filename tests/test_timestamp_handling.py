#!/usr/bin/env python
"""
Test suite for timestamp handling in the crypto pricing service.
Tests verify that:
1. Users can provide explicit timestamps for past dates
2. When no timestamp is provided, one is generated close to the current time
"""

import pytest
import json
import uuid
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import time

# Add the project root to the Python path if needed
import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import necessary modules
from main import app, publish_message_to_pubsub
from common.models.http_query_params import PostData
from common.models.date_time_iso8601 import ApprovedDateTime as DateTime
from fastapi.testclient import TestClient

# Create test client
client = TestClient(app)

# Helper functions
def generate_iso_timestamp(days_ago=0, hours_ago=0, minutes_ago=0, seconds_ago=0):
    """Generate ISO 8601 timestamp for a given time in the past."""
    dt = datetime.now(timezone.utc) - timedelta(
        days=days_ago,
        hours=hours_ago,
        minutes=minutes_ago,
        seconds=seconds_ago
    )
    return dt.isoformat()

def is_close_to_now(timestamp_str, tolerance_seconds=5):
    """
    Check if a timestamp string is close to the current time.
    
    Args:
        timestamp_str: ISO 8601 timestamp string
        tolerance_seconds: Maximum allowed difference in seconds
        
    Returns:
        bool: True if timestamp is within tolerance of current time
    """
    if not timestamp_str:
        return False
        
    # Parse the timestamp string to a datetime object
    try:
        timestamp = DateTime(timestamp_str).to_datetime()
    except (ValueError, TypeError):
        return False
        
    # Get current time
    now = datetime.now(timezone.utc)
    
    # Calculate time difference in seconds
    diff = abs((now - timestamp).total_seconds())
    
    # Check if within tolerance
    return diff <= tolerance_seconds


class TestTimestampHandling:
    """Test timestamp handling in the API."""

    def setup_method(self):
        """Setup for each test."""
        self.valid_base_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "test-api",
            "open": 50000.0,
            "close": 51000.0,
            "high": 52000.0,
            "low": 49000.0,
            "volume": 1000.0,
            "ticker": "BTC-USD"
        }

    @patch('google.cloud.pubsub_v1.PublisherClient')
    def test_explicit_past_timestamp(self, mock_publisher_class):
        """Test that explicit past timestamps are accepted and preserved."""
        # Setup mock
        mock_publisher = mock_publisher_class.return_value
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"
        
        mock_future = MagicMock()
        mock_future.result.return_value = "test-message-id"
        mock_publisher.publish.return_value = mock_future
        
        # Create explicit past timestamps
        past_dates = [
            generate_iso_timestamp(days_ago=1),    # Yesterday
            generate_iso_timestamp(days_ago=7),    # Last week
            generate_iso_timestamp(days_ago=30),   # Last month
            generate_iso_timestamp(days_ago=365),  # Last year
            "2020-01-01T00:00:00Z"                 # Fixed past date
        ]
        
        for past_date in past_dates:
            # Prepare test data with explicit timestamp
            test_data = {**self.valid_base_data, "timestamp": past_date}
            
            # Make API request
            response = client.post("/prices", json=[test_data])
            
            # Verify successful response
            assert response.status_code == 201
            
            # Verify the timestamp was accepted and passed through to Pub/Sub
            publish_call = mock_publisher.publish.call_args
            published_data = json.loads(publish_call[0][1].decode('utf-8'))
            
            # Check that the original timestamp was preserved
            assert published_data["timestamp"] == past_date
            
            # Reset mock for next iteration
            mock_publisher.reset_mock()

    @patch('google.cloud.pubsub_v1.PublisherClient')
    def test_missing_timestamp_auto_generation(self, mock_publisher_class):
        """Test that a timestamp is auto-generated when not provided."""
        # Setup mock
        mock_publisher = mock_publisher_class.return_value
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"
        
        mock_future = MagicMock()
        mock_future.result.return_value = "test-message-id"
        mock_publisher.publish.return_value = mock_future
        
        # Prepare test data without a timestamp
        test_data = {k: v for k, v in self.valid_base_data.items()}
        
        # Add timestamp at the model level
        post_data = PostData(**test_data)
        assert hasattr(post_data, 'timestamp')
        assert post_data.timestamp is not None
        
        # Verify the auto-generated timestamp is close to now
        assert isinstance(post_data.timestamp, DateTime)
        assert is_close_to_now(str(post_data.timestamp))
        
        # Test through the API to verify end-to-end behavior
        response = client.post("/prices", json=[test_data])
        
        # Verify successful response
        assert response.status_code == 201
        
        # Verify the generated timestamp was passed through to Pub/Sub
        publish_call = mock_publisher.publish.call_args
        published_data = json.loads(publish_call[0][1].decode('utf-8'))
        
        # Check that a timestamp was included and is close to now
        assert "timestamp" in published_data
        assert is_close_to_now(published_data["timestamp"])

    def test_model_level_timestamp_handling(self):
        """Test timestamp handling at the Pydantic model level."""
        # Test with explicit timestamp
        explicit_time = "2023-01-01T12:00:00Z"
        model_with_explicit = PostData(**{**self.valid_base_data, "timestamp": explicit_time})
        
        # Verify explicit timestamp is preserved and converted to DateTime
        assert isinstance(model_with_explicit.timestamp, DateTime)
        assert str(model_with_explicit.timestamp) == explicit_time
        
        # Test with no timestamp (should auto-generate)
        model_without_timestamp = PostData(**self.valid_base_data)
        
        # Verify timestamp was generated and is a DateTime
        assert isinstance(model_without_timestamp.timestamp, DateTime)
        assert is_close_to_now(str(model_without_timestamp.timestamp))
        
        # Verify different times give different timestamps (no caching)
        time.sleep(0.01)  # Small delay to ensure different timestamps
        model_without_timestamp2 = PostData(**self.valid_base_data)
        assert str(model_without_timestamp.timestamp) != str(model_without_timestamp2.timestamp)

    def test_different_timestamp_formats(self):
        """Test that different timestamp formats are correctly handled."""
        formats = [
            "2023-01-01T12:00:00Z",                      # UTC
            "2023-01-01T12:00:00+00:00",                 # Explicit +00:00
            "2023-01-01T07:00:00-05:00",                 # EST
            "2023-01-01T17:00:00+05:00",                 # +5 UTC
            "2023-01-01 12:00:00Z",                      # Space instead of T
            "2023-01-01",                                # Date only (should interpret as UTC midnight)
        ]
        
        for fmt in formats:
            # Create a model with the test format
            model = PostData(**{**self.valid_base_data, "timestamp": fmt})
            
            # Verify it's a DateTime instance
            assert isinstance(model.timestamp, DateTime)
            
            # Get the UTC datetime for comparison
            dt = DateTime(fmt).to_datetime()
            assert dt.tzinfo is not None  # Ensure timezone awareness


class TestTimestampEdgeCases:
    """Test edge cases for timestamp handling."""

    def setup_method(self):
        """Setup for each test."""
        self.valid_base_data = {
            "crypto_name": "Bitcoin",
            "crypto_symbol": "BTC",
            "fiat_currency": "USD",
            "source": "test-api",
            "open": 50000.0,
            "close": 51000.0,
            "high": 52000.0,
            "low": 49000.0,
            "volume": 1000.0,
            "ticker": "BTC-USD"
        }

    def test_future_timestamp(self):
        """Test handling of future timestamps."""
        # Create a timestamp slightly in the future
        future_time = generate_iso_timestamp(days_ago=-1)  # 1 day in the future
        
        # Try to create a model with a future timestamp
        try:
            model = PostData(**{**self.valid_base_data, "timestamp": future_time})
            # If no exception, check if the model normalized the timestamp to now
            # or if future timestamps are allowed
            assert isinstance(model.timestamp, DateTime)
        except ValueError as e:
            # If validation error, that's an acceptable behavior too
            assert "future" in str(e).lower() or "timestamp" in str(e).lower()

    def test_invalid_timestamp_formats(self):
        """Test handling of invalid timestamp formats."""
        invalid_formats = [
            "not-a-date",                     # Completely invalid
            "01/01/2023",                     # MM/DD/YYYY format
            "2023-13-01T00:00:00Z",           # Invalid month
            "2023-01-32T00:00:00Z",           # Invalid day
            "2023-01-01T25:00:00Z",           # Invalid hour
            "2023/01/01",                     # Wrong separator
        ]
        
        for invalid_fmt in invalid_formats:
            # Try to create a model with an invalid format
            try:
                model = PostData(**{**self.valid_base_data, "timestamp": invalid_fmt})
                # If no exception, the model might have done best-effort parsing
                # Ensure it's still a DateTime object
                assert isinstance(model.timestamp, DateTime)
            except ValueError:
                # Exception for invalid format is expected behavior
                pass


if __name__ == "__main__":
    pytest.main(["-xvs", "test_timestamp_handling.py"])