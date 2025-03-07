# Crypto Pricing Service

A GCP Cloud Function service that handles cryptocurrency pricing data, validates it, and publishes to PubSub with AVRO schema validation.

## Overview

The Crypto Pricing Service is a microservice built on Google Cloud Platform that:

1. Accepts cryptocurrency pricing data via HTTP POST requests
2. Validates the data using Pydantic models
3. Publishes the data to a Google Cloud Pub/Sub topic for further processing
4. Provides detailed responses about successful and failed operations

The service is designed to be deployed as a Google Cloud Function (Gen2) and follows best practices for reliability, security, and maintainability.

## Project Structure

```
.
├── Makefile                      # Build and deployment automation
├── README.md                     # This file
├── avro_schema.avsc              # AVRO schema for Pub/Sub messages
├── common/                       # Shared library code
│   ├── __init__.py
│   ├── csv_response.py           # CSV response formatter
│   ├── database/                 # Database integration modules
│   ├── extract_openapi.py        # OpenAPI spec extractor
│   ├── fastapi_app.py            # FastAPI application factory
│   ├── format_response.py        # Response formatter utilities
│   ├── local_runner.py           # Local development server
│   ├── logging_utils.py          # Structured logging utilities
│   ├── models/                   # Pydantic data models
│   ├── openapi_utils.py          # OpenAPI specification utilities
│   └── vellox_handler.py         # Cloud Function handler utility
├── main.py                       # Main application entry point
├── requirements.txt              # Python dependencies
└── tests/                        # Test suite
    ├── README.md                 # Test documentation
    ├── conftest.py               # Test configuration and fixtures
    ├── test_avro_schema.py       # AVRO schema validation tests
    ├── test_e2e.py               # End-to-end flow tests
    ├── test_may_api.py           # API validation tests
    ├── test_pub_sub_integration.py # Pub/Sub integration tests
    └── test_validation.py        # Data validation tests
```

## Prerequisites

- Python 3.12 or higher
- Google Cloud SDK
- Access to a Google Cloud Project with Pub/Sub and Cloud Functions enabled
- Appropriate IAM permissions to deploy Cloud Functions and publish to Pub/Sub

## Setup

### Local Development Environment

1. Clone the repository
2. Install dependencies:

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows, use .venv\Scripts\activate

# Install dependencies
make build
```

### Environment Variables

The following environment variables are used:

- `FUNCTION_NAME`: Name of the deployed function (default: "post_prices")
- `DEPLOYED_VERSION`: Version identifier
- `LOG_FILE_NAME`: Log file name (default: "pricing-service")
- `LOG_SERVICE_NAME`: Service name for logging
- `LOG_FUNCTION_NAME`: Function name for logging
- `ENVIRONMENT`: Deployment environment (e.g., "dev-test-staging", "local")

## Running Locally

Use the Makefile to run the service locally:

```bash
# Run with standard output
make run

# Run with debug output
make debug
```

The service will be available at http://localhost:8080

## Deployment

### Deploy to Google Cloud Functions

```bash
make deploy
```

This will:
1. Clean the build environment
2. Copy the common library
3. Deploy to Google Cloud Functions Gen2

### Manual Deployment

You can also deploy manually using the gcloud CLI:

```bash
gcloud functions deploy post_prices \
  --gen2 \
  --runtime python312 \
  --source . \
  --region us-central1 \
  --trigger-http \
  --memory 512M \
  --set-env-vars DEPLOYED_VERSION_NAME=1.0.GIT_SHA,FUNCTION_NAME=post_prices,LOG_FILE_NAME="pricing-service",LOG_SERVICE_NAME=pricing-service,LOG_FUNCTION_NAME=post_prices,ENVIRONMENT=dev-test-staging \
  --entry-point handler \
  --allow-unauthenticated
```

## API Documentation

### POST /prices

Creates new cryptocurrency price records.

#### Request

Content-Type: `application/json`

Body: Array of price records

```json
[
  {
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
    "timestamp": "2025-02-01T16:13:56.604630+00:00",
    "dividends": 0.0,
    "stock_splits": 0.0,
    "metadata": "{\"source_details\":{\"reliability\":\"high\"},\"tags\":[\"popular\",\"volatile\"]}"
  }
]
```

#### Required Fields

- `crypto_name`: Full name of the cryptocurrency
- `crypto_symbol`: Symbol of the cryptocurrency (e.g., BTC, ETH)
- `fiat_currency`: Fiat currency the price is denominated in (e.g., USD, EUR)
- `source`: Source of the data
- `open`: Opening price
- `close`: Closing price
- `high`: Highest price during the period
- `low`: Lowest price during the period
- `volume`: Trading volume
- `ticker`: Ticker symbol
- `timestamp`: ISO 8601 timestamp for the price data

#### Optional Fields

- `dividends`: Dividends paid (defaults to 0.0)
- `stock_splits`: Stock splits (defaults to 0.0)
- `metadata`: JSON string with additional metadata (defaults to empty string)

#### Responses

- `201 Created`: All records created successfully
- `207 Multi-Status`: Partial success (some records created, some failed)
- `202 Accepted`: No records created (all failed)
- `422 Unprocessable Entity`: Invalid request data

#### Success Response (201)

```json
{
  "status": "success",
  "data": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "message_id": "1234567890"
    }
  ],
  "metadata": {
    "rows": 1,
    "start_timestamp": "2025-03-07T12:00:00.000000Z",
    "finish_timestamp": "2025-03-07T12:00:01.000000Z"
  }
}
```

#### Partial Success Response (207)

```json
{
  "status": "partial success, some records created",
  "data": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "message_id": "1234567890"
    },
    {
      "id": "223e4567-e89b-12d3-a456-426614174000",
      "error": "Pub/Sub error",
      "input_data": { /* Original input data */ }
    }
  ],
  "metadata": {
    "rows": 2,
    "start_timestamp": "2025-03-07T12:00:00.000000Z",
    "finish_timestamp": "2025-03-07T12:00:01.000000Z"
  }
}
```

## Testing

The project includes a comprehensive test suite:

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run tests with coverage
pytest --cov=. --cov-report=html

# Run a specific test file
pytest tests/test_e2e.py
```

## AVRO Schema

The service uses an AVRO schema for Pub/Sub messages. The schema is defined in `avro_schema.avsc`.

Key points about the schema:

- All required fields must be present
- `metadata` is always a string, never null (empty string used as default)
- Timestamps must be in ISO 8601 format
- Boolean fields are properly formatted for AVRO

## Development Guidelines

- Follow the "Power of Ten" Python coding standards in the documentation
- Use Pydantic models for data validation
- Write comprehensive tests for new features
- Ensure AVRO schema compliance for messages

## Logging

The service uses structured logging with different levels:

- `debug`: Detailed debugging information
- `info`: General operational information
- `warning`: Warning events that might cause issues
- `error`: Error events that might still allow the application to continue
- `exception`: Critical errors that prevent proper functioning
- `audit`: Special events that should be recorded for auditing

Logs are color-coded in the local environment and sent to Google Cloud Logging in production.

## Contributing

1. Ensure your code passes all tests
2. Follow the "Power of Ten" coding standards
3. Add appropriate tests for new functionality
4. Update documentation as needed

## License

[Your License Here]