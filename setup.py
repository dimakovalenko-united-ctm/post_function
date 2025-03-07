"""
Setup script for the crypto-pricing-service package.
This allows the package to be installable in development mode,
which helps with imports in tests.
"""

from setuptools import setup, find_packages

setup(
    name="crypto-pricing-service",
    version="1.0.0",
    description="Cryptocurrency pricing service for GCP",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(include=["."]),
    python_requires=">=3.12",
)