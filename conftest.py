"""
Configuration file for pytest.
This file adds the current directory to the Python path so that
modules can be imported properly during testing.
"""

import os
import sys

# Add the project root directory to the Python path
# This allows importing modules from the root directory
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)