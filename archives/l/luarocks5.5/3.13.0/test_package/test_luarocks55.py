#!/usr/bin/env python3
"""Runtime checks for the LuaRocks 3.13.0 package configured for Lua 5.5."""

import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(args, expect_success=True):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    output = result.stdout
    if expect_success and result.returncode != 0:
        raise AssertionError(f"{args!r} failed with {result.returncode}\n{output}")
    if not expect_success and result.returncode == 0:
        raise AssertionError(f"{args!r} unexpectedly succeeded\n{output}")
    return output


def main():
    if len(sys.argv) != 3:
        raise AssertionError("usage: test_luarocks55.py <luarocks> <luarocks-admin>")
    luarocks = sys.argv[1]
    luarocks_admin = sys.argv[2]

    version = run_command([luarocks, "--version"])
    assert "3.13.0" in version

    lua_version = run_command([luarocks, "config", "lua_version"])
    assert "5.5" in lua_version

    admin_version = run_command([luarocks_admin, "--version"])
    assert "3.13.0" in admin_version

    help_output = run_command([luarocks, "help", "install"])
    assert "install" in help_output.lower()

    invalid_command = run_command([luarocks, "definitely-not-a-luarocks-command"], expect_success=False)
    assert "unknown command" in invalid_command.lower() or "unknown" in invalid_command.lower()

    with tempfile.TemporaryDirectory() as tmp:
        bad_rockspec = Path(tmp) / "bad-0.1-1.rockspec"
        bad_rockspec.write_text('package = "bad"\nversion = "0.1-1"\nsource = {}\n', encoding="utf-8")
        lint_output = run_command([luarocks, "lint", str(bad_rockspec)], expect_success=False)
        assert "rockspec" in lint_output.lower() or "missing" in lint_output.lower()

    print("luarocks5.5 smoke and fault-injection checks passed")


if __name__ == "__main__":
    main()
