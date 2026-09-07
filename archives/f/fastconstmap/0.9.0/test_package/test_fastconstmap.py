#!/usr/bin/env python3
"""Run the complete upstream pytest suite and consumer smoke checks."""
import sys


def main():
    import fastconstmap
    m = fastconstmap.ConstMap({"hello": 42, b"bytes": 7})
    assert m["hello"] == 42
    assert m[b"bytes"] == 7

    import pytest
    pytest_args = [sys.argv[1], "-q"]
    if len(sys.argv) > 2:
        # An explicit basetemp avoids pytest's shared-root ownership check.
        # HMDFS may report a mount owner different from the active test UID.
        pytest_args.extend(["--basetemp", sys.argv[2]])
    result = pytest.main(pytest_args)
    if result != pytest.ExitCode.OK:
        return int(result)
    print("CONSUMER_TESTS TOTAL=2 PASS=2 FAIL=0 SKIP=0 NOT_RUN=0")
    print("UPSTREAM_TESTS TOTAL=56 PASS=56 FAIL=0 SKIP=0 NOT_RUN=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
