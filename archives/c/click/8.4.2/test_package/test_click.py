#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script for click package — verifies import, version, and CLI API."""

import sys

failed = False

try:
    import click

    print(f"✓ click imported successfully")
    print(f"✓ click version: {click.__version__}")

    # Verify click.command decorator is callable (core CLI API)
    assert hasattr(click, "command"), "click should expose 'command' decorator"
    assert callable(click.command), "click.command should be callable"
    print("✓ click.command decorator is callable")

    # Verify click.option decorator is callable (commonly used CLI helper)
    assert hasattr(click, "option"), "click should expose 'option' decorator"
    assert callable(click.option), "click.option should be callable"
    print("✓ click.option decorator is callable")

except ImportError as e:
    print(f"✗ Failed to import click: {e}")
    sys.exit(1)
except AssertionError as e:
    print(f"✗ API assertion failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All tests passed!")
sys.exit(0)
