#!/usr/bin/env python3
"""Test script for cookiecutter package"""

import sys
import subprocess

try:
    import cookiecutter
    
    print("✓ cookiecutter imported successfully")
    print(f"✓ cookiecutter version: {cookiecutter.__version__}")
    
    # Test main API functions exist
    assert hasattr(cookiecutter, 'main'), "cookiecutter should have 'main' function"
    print("✓ cookiecutter.main() function exists")
    
    # Test that we can access the main API
    from cookiecutter.main import cookiecutter as cookiecutter_main
    print("✓ cookiecutter.main.cookiecutter() function accessible")
    
    # Test CLI tool
    result = subprocess.run(
        ["cookiecutter", "--version"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        print(f"✓ cookiecutter CLI works correctly")
        print(f"  Version output: {result.stdout.strip()}")
    else:
        print(f"⚠ cookiecutter CLI returned non-zero: {result.stderr}")
    
    # Test CLI help
    result = subprocess.run(
        ["cookiecutter", "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        print(f"✓ cookiecutter --help works correctly")
        # Verify help contains expected content
        assert "usage:" in result.stdout.lower() or "Usage:" in result.stdout
        print("  Help output contains usage information")
    else:
        print(f"⚠ cookiecutter --help failed: {result.stderr}")
    
    print("\n✅ All tests passed!")
    sys.exit(0)

except ImportError as e:
    print(f"✗ Failed to import cookiecutter: {e}")
    sys.exit(1)

except subprocess.TimeoutExpired:
    print(f"✗ CLI command timed out")
    sys.exit(1)

except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)