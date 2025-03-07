#!/usr/bin/env python
"""
A utility script to debug import issues by listing:
1. Python version
2. Current working directory
3. sys.path
4. Available modules in the project
5. Basic import test for key modules
"""

import sys
import os
import importlib
import inspect
from pathlib import Path

# Print Python version and environment
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")

# Add project root to path if not already there
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"Added {project_root} to sys.path")

# Print sys.path
print("\nPython module search paths (sys.path):")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")

# Try importing main modules and verify paths
print("\nAttempting to import key modules:")

modules_to_check = [
    'main', 
    'common',
    'common.models.http_query_params',
    'common.models.approved_uuid',
    'common.models.date_time_iso8601'
]

for module_name in modules_to_check:
    try:
        module = importlib.import_module(module_name)
        print(f"✅ Successfully imported {module_name} from {module.__file__}")
        
        # If it's the main module, show the app details
        if module_name == 'main':
            if hasattr(module, 'app'):
                print(f"  - FastAPI app found: {module.app}")
            else:
                print(f"  - Warning: No 'app' attribute found in main module")
        
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
    except Exception as e:
        print(f"❌ Error with {module_name}: {e}")

# Check for common directory structure
print("\nChecking common directory:")
common_dir = os.path.join(project_root, 'common')
if os.path.exists(common_dir):
    if os.path.islink(common_dir):
        target = os.readlink(common_dir)
        print(f"  'common' is a symlink pointing to: {target}")
    elif os.path.isdir(common_dir):
        print(f"  'common' is a regular directory")
    print(f"  Contents: {os.listdir(common_dir)}")
else:
    print(f"  'common' directory not found")

# Print all Python files in the project
print("\nPython files in the project:")
for path in Path(project_root).rglob("*.py"):
    rel_path = os.path.relpath(path, project_root)
    print(f"  {rel_path}")

print("\nDebugging complete")