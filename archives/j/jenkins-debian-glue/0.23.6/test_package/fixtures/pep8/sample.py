#!/usr/bin/env python3
"""Minimal Python fixture for the jdg-tap-pep8 mimetype-gate test.

The gate must recognize this file as Python (via `file -b` + /python/i)
and hand it to pycodestyle/pep8. The tool itself is not installed on the
OHOS worker, so the test only asserts the gate decision, not lint output.
"""
import os

print(os.getcwd())
