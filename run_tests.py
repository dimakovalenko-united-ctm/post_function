#!/usr/bin/env python
"""
A Python-based test runner script that sets up the environment correctly 
and runs the tests with proper path configuration.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def colorize(text, color_code):
    """Add color to terminal output."""
    return f"\033[{color_code}m{text}\033[0m"

def green(text):
    return colorize(text, "1;32")

def yellow(text):
    return colorize(text, "1;33")

def red(text):
    return colorize(text, "1;31")

def setup_environment():
    """Set up the testing environment."""
    # Get project root
    project_root = Path(__file__).resolve().parent
    
    # Add project root to Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        os.environ['PYTHONPATH'] = str(project_root)
        print(yellow(f"Added {project_root} to PYTHONPATH"))
    
    # Check for common directory and create symlink if needed
    common_dir = project_root / 'common'
    if not common_dir.exists():
        print(yellow("Creating symlink to common directory..."))
        try:
            parent_common = Path("../../common")
            if parent_common.exists():
                os.symlink(parent_common, common_dir)
                print(green("Created symlink to ../../common"))
            else:
                print(red("../../common directory not found"))
                return False
        except Exception as e:
            print(red(f"Error creating symlink: {e}"))
            return False
    
    # Set environment variable to indicate we're in a test environment
    os.environ['ENVIRONMENT'] = 'local'
    os.environ.setdefault('FUNCTION_NAME', 'post_prices')
    
    return True

def run_tests(test_args):
    """Run the tests with the given arguments."""
    cmd = [sys.executable, "-m", "pytest"] + test_args
    
    print(yellow(f"Running tests with command: {' '.join(cmd)}"))
    try:
        subprocess.run(cmd, check=True)
        print(green("\nTests completed successfully!"))
        return True
    except subprocess.CalledProcessError:
        print(red("\nTests failed."))
        return False

def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description='Run tests with proper environment setup')
    parser.add_argument('tests', nargs='*', default=['tests/'], help='Test files or directories to run')
    parser.add_argument('-v', '--verbose', action='store_true', help='Run tests in verbose mode')
    parser.add_argument('-x', '--exitfirst', action='store_true', help='Exit on first failure')
    
    args = parser.parse_args()
    
    test_args = args.tests
    if args.verbose:
        test_args.append('-v')
    if args.exitfirst:
        test_args.append('-x')
    
    print(yellow("Setting up test environment..."))
    if not setup_environment():
        sys.exit(1)
    
    success = run_tests(test_args)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()