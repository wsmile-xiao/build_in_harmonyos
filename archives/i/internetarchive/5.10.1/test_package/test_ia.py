#!/usr/bin/env python3
"""Test script for internetarchive 5.10.1 — import + CLI entry point verification."""
import sys

def test_import():
    try:
        import internetarchive
        ver = internetarchive.__version__
        assert ver == "5.10.1", f"version mismatch: {ver} != 5.10.1"
        print(f"PASS: internetarchive {ver} imported successfully")
        return True
    except Exception as e:
        print(f"FAIL: import error: {e}", file=sys.stderr)
        return False

def test_cli():
    try:
        from internetarchive.cli.ia import main
        assert callable(main), "main is not callable"
        print("PASS: CLI entry point (ia) found and callable")
        return True
    except Exception as e:
        print(f"FAIL: CLI error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    results = [test_import(), test_cli()]
    if all(results):
        print("\nAll internetarchive tests passed.")
        sys.exit(0)
    else:
        print(f"\n{sum(1 for r in results if not r)} test(s) FAILED", file=sys.stderr)
        sys.exit(1)
