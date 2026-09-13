#!/usr/bin/env python3
"""Consumer checks for the installed cronutils command set."""

import os
import shutil
import subprocess
import sys
import time


checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


def run(command, *args, timeout=10):
    return subprocess.run(
        [command, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_cronutils.py <package-bin-dir>")

    bin_dir = os.path.abspath(sys.argv[1])
    binaries = {
        name: os.path.join(bin_dir, name)
        for name in ("runalarm", "runlock", "runstat")
    }
    for name, path in binaries.items():
        check(os.path.isfile(path), f"{name} is missing from the package")

    for name, path in binaries.items():
        result = run(path, "-h")
        output = (result.stdout or "") + (result.stderr or "")
        check(result.returncode == 0, f"{name} -h returned {result.returncode}")
        check("Usage:" in output, f"{name} -h did not print usage")

    python_exe = sys.executable
    result = run(
        binaries["runalarm"],
        python_exe,
        "-c",
        "import sys; sys.exit(7)",
    )
    check(result.returncode == 7, "runalarm did not forward the child status")

    result = run(
        binaries["runalarm"],
        "-t",
        "1",
        python_exe,
        "-c",
        "import time; time.sleep(5)",
        timeout=10,
    )
    check(result.returncode == 142, "runalarm timeout status mismatch")

    work_dir = os.path.join(os.getcwd(), ".cronutils-test")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    try:
        lock_path = os.path.join(work_dir, "job.lock")
        first = subprocess.Popen(
            [
                binaries["runlock"],
                "-f",
                lock_path,
                python_exe,
                "-c",
                "import time; time.sleep(3)",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.25)
        check(os.path.isfile(lock_path), "runlock did not create the lock file")

        second = run(
            binaries["runlock"],
            "-f",
            lock_path,
            "-t",
            "1",
            python_exe,
            "-c",
            "pass",
            timeout=5,
        )
        first_status = first.wait(timeout=5)
        check(first_status == 0, "runlock owner process failed")
        check(
            second.returncode == 73,
            "runlock did not return EX_CANTCREAT for a held lock",
        )

        stats_path = os.path.join(work_dir, "job.stat")
        result = run(
            binaries["runstat"],
            "-f",
            stats_path,
            python_exe,
            "-c",
            "import sys; sys.exit(7)",
        )
        check(result.returncode == 7, "runstat did not forward the child status")
        check(os.path.isfile(stats_path), "runstat did not write its statistics file")
        with open(stats_path, encoding="utf-8") as stream:
            stats = stream.read()
        check(",exit_status,7," in stats, "runstat exit_status record is missing")
        check(",elapsed_time," in stats, "runstat elapsed_time record is missing")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    expected_checks = 18
    if checks != expected_checks:
        raise AssertionError("consumer assertion count mismatch")
    print(
        f"PASS: cronutils packaged consumer test "
        f"({checks}/{expected_checks} assertions)"
    )


if __name__ == "__main__":
    main()
