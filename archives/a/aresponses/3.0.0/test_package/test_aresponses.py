#!/usr/bin/env python3
"""Test script for aresponses — R34 compliant.

This test imports aresponses and exercises its API to verify
the package is correctly installed and functional.
"""
import sys


def main():
    # Import the package
    from aresponses import ResponsesMockServer
    from aresponses import aresponses as aresponses_fixture
    from aresponses.errors import NoRouteFoundError

    # Verify the main class exists and has expected methods
    assert hasattr(ResponsesMockServer, '__init__'), "ResponsesMockServer missing __init__"
    assert hasattr(ResponsesMockServer, 'add'), "ResponsesMockServer missing add method"
    assert hasattr(ResponsesMockServer, 'passthrough'), "ResponsesMockServer missing passthrough method"

    # Verify the pytest fixture decorator exists
    assert callable(aresponses_fixture), "aresponses fixture is not callable"

    # Verify error class exists
    assert issubclass(NoRouteFoundError, Exception), "NoRouteFoundError is not an Exception"

    print("aresponses import and API test: PASSED")
    print(f"  - ResponsesMockServer: OK")
    print(f"  - aresponses fixture: OK")
    print(f"  - NoRouteFoundError: OK")

    return 0


if __name__ == "__main__":
    sys.exit(main())
