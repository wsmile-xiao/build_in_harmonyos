#!/usr/bin/env python3
"""Consumer smoke tests for the packaged mysqltuner CLI."""
import os
import subprocess
import sys
from pathlib import Path


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def run_perl(perl, script, *args):
    env = os.environ.copy()
    env["PATH"] = str(script.parent) + os.pathsep + env.get("PATH", "")
    return subprocess.run(
        [str(perl), str(script), *args],
        cwd=str(script.parent),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_mysqltuner.py <package_folder> <perl>")

    package_folder = Path(sys.argv[1])
    perl = Path(sys.argv[2])
    script = package_folder / "bin" / "mysqltuner"
    script_alias = package_folder / "bin" / "mysqltuner.pl"
    data_dir = package_folder / "share" / "mysqltuner"

    assert_true(perl.is_file(), "Perl executable exists")
    assert_true(script.is_file(), "mysqltuner launcher exists")
    assert_true(script_alias.is_file(), "mysqltuner.pl launcher alias exists")
    assert_true((data_dir / "basic_passwords.txt").is_file(), "basic password data exists")
    assert_true((data_dir / "vulnerabilities.csv").is_file(), "vulnerability data exists")
    assert_true((package_folder / "licenses" / "LICENSE").is_file(), "license is packaged")

    first_line = script.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    assert_true(first_line.startswith("#!"), "launcher keeps a shebang")

    help_run = run_perl(perl, script, "--help")
    assert_true(help_run.returncode == 0, "--help returns success")
    assert_true("MySQLTuner" in help_run.stdout, "--help mentions MySQLTuner")
    assert_true("--host <host>" in help_run.stdout, "--help documents host option")
    assert_true("--json" in help_run.stdout, "--help documents JSON option")

    forced_help = run_perl(perl, script, "--forcemem", "2G", "--forceswap", "512M", "--help")
    assert_true(forced_help.returncode == 0, "human memory CLI values are accepted")

    bad_port = run_perl(perl, script, "--port", "abc")
    assert_true(bad_port.returncode != 0, "invalid port is rejected")


if __name__ == "__main__":
    main()
