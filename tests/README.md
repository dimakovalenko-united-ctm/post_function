# Pricing Service Test Suite

This repository contains a comprehensive test suite for the Pricing Service API, focusing on validating the correct handling of cryptocurrency pricing data through the API and Pub/Sub integration.

## Overview

The test suite covers:

1. API validation and schema conformance
2. Pub/Sub message formatting and delivery
3. AVRO schema validation
4. End-to-end flow testing
5. Error handling and edge cases

## Test Structure

The tests are organized into several files, each focusing on specific aspects of the service:

- `test_main_api.py` - Tests the FastAPI endpoints, validation, and responses
- `test_validation.py` - Tests data validation for the Pydantic models
- `test_pubsub_integration.py` - Tests the Pub/Sub integration and message formatting
- `test_avro_schema.py` - Tests AVRO schema compliance
- `test_e2e.py` - End-to-end tests of the complete flow

## Running the Tests

### Prerequisites

1. Python 3.12 or higher
2. The required packages installed:
   ```
   pip install pytest pytest-cov fastapi httpx
   ```

### Execute the Tests

Run all tests:
```
pytest
```

Run with coverage:
```
pytest --cov=. --cov-report=html
```

Run a specific test file:
```
pytest test_main_api.py
```

## Test Guidelines

When adding new tests or modifying existing ones, please follow these guidelines:

1. **Isolated Tests**: Each test should be isolated and not depend on the state of other tests
2. **Mock External Services**: All external services (Pub/Sub, databases) should be mocked
3. **Descriptive Names**: Use descriptive test names that indicate what is being tested
4. **Assertions**: Include meaningful assertions that validate the expected behavior
5. **Edge Cases**: Include tests for edge cases and error conditions

## Common Test Fixtures

The `conftest.py` file contains shared fixtures used across multiple test files, including:

- Sample payloads (valid, invalid, minimal)
- Mocked Pub/Sub clients
- FastAPI test client

## Security Testing

The test suite includes tests for common security concerns:

- SQL injection attempts
- XSS (Cross-Site Scripting) attempts
- JSON injection
- Input validation

## AVRO Schema Validation

The tests verify that messages conform to the AVRO schema requirements, with special attention to:

- Required fields
- Field types
- Metadata handling (never null)
- Boolean representation

## Contributing

When adding new tests:

1. Create or update the appropriate test file
2. Use existing fixtures where applicable
3. Follow the naming convention: `test_[what]_[condition]`
4. Add appropriate assertions
5. Update this README if needed