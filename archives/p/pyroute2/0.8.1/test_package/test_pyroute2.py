#!/usr/bin/env python3
"""Consumer test for pyroute2 0.8.1 — import API and exercise pure helpers."""
import sys


def test_import_and_version():
    import pyroute2

    ver = pyroute2.__version__
    assert ver == "0.8.1", f"version mismatch: {ver} != 0.8.1"
    print(f"PASS: pyroute2 {ver} imported successfully")


def test_netlink_error_aliases():
    """Cover the offline half of upstream test_exceptions (E1 == E2 == E3).

    Upstream also opens AF_NETLINK via IPRoute(); that part stays exempted
    on OHOS workers without CAP_NET_ADMIN. Class-identity needs no socket.
    """
    from pyroute2 import NetlinkError as E1
    from pyroute2.netlink import NetlinkError as E2
    from pyroute2.netlink.exceptions import NetlinkError as E3

    assert E1 == E2 == E3
    print("PASS: NetlinkError aliases are identical (E1 == E2 == E3)")


def test_common_helpers():
    from pyroute2.common import dqn2int, hexdump, hexload

    assert dqn2int("255.255.255.0") == 24
    binary = b"abcdef5678"
    dump = hexdump(binary)
    assert hexload(dump) == binary
    print("PASS: pyroute2.common helpers (dqn2int/hexdump) work")


def test_public_symbols():
    from pyroute2 import IPRoute, IPSet, NDB

    assert IPRoute is not None
    assert IPSet is not None
    assert NDB is not None
    print("PASS: public symbols IPRoute/IPSet/NDB are importable")


def test_cli_entry_points():
    from pyroute2.ndb.cli import run as cli_run
    from pyroute2.decoder.main import run as decoder_run
    from pyroute2.config.test_platform import run as platform_run

    assert callable(cli_run)
    assert callable(decoder_run)
    assert callable(platform_run)
    print("PASS: CLI entry points are callable")


if __name__ == "__main__":
    tests = [
        test_import_and_version,
        test_netlink_error_aliases,
        test_common_helpers,
        test_public_symbols,
        test_cli_entry_points,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
        except Exception as e:
            print(f"FAIL: {fn.__name__}: {e}", file=sys.stderr)
            failed += 1
    if failed:
        print(f"\n{failed} test(s) FAILED", file=sys.stderr)
        sys.exit(1)
    print("\nAll pyroute2 consumer tests passed.")
    sys.exit(0)
