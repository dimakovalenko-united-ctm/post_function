#!/usr/bin/env python
from pydantic import BaseModel, constr, validator
from typing import Set

# Define the valid fiat currencies
VALID_FIAT_CURRENCIES: Set[str] = {
    'USD', 'EUR', 'GBP', 
    'JPY', 'AUD', 'CAD', 
    'CHF', 'CNY', 'INR'
}

class FiatCurrencyModel(BaseModel):
    currency: str  # Field to hold the currency code

    @validator('currency')
    def validate_currency(cls, value: str) -> str:
        """
        Validator to ensure the currency is in the VALID_FIAT_CURRENCIES set.
        """
        if value not in VALID_FIAT_CURRENCIES:
            raise ValueError(f"Invalid currency: {value}. Must be one of {VALID_FIAT_CURRENCIES}")
        return value