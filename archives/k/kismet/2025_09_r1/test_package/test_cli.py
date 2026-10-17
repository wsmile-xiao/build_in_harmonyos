#!/usr/bin/env python3
import shutil
import subprocess
import sys


DEFAULT_TIMEOUT_SECONDS = 60


def _captured_output(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value)


def run_command(
    args,
    *,
    expected_returncodes,
    expect_failure=False,
    timeout=DEFAULT_TIMEOUT_SECONDS,
):
    executable = shutil.which(args[0])
    if not executable:
        raise SystemExit(f"{args[0]} was not found in PATH")

    try:
        completed = subprocess.run(
            [executable, *args[1:]],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = _captured_output(exc.stdout)
        if output:
            print(output)
        raise SystemExit(
            f"{' '.join(args)} timed out after {timeout} seconds"
        ) from exc

    output = completed.stdout or ""
    print(output)

    if completed.returncode not in expected_returncodes:
        raise SystemExit(
            f"{' '.join(args)} returned {completed.returncode}, "
            f"expected one of {sorted(expected_returncodes)}"
        )
    if expect_failure and completed.returncode == 0:
        raise SystemExit(f"{' '.join(args)} unexpectedly succeeded")
    return output


def main():
    version_output = run_command(["kismet", "--version"], expected_returncodes={0, 1})
    if "Kismet" not in version_output:
        raise SystemExit("kismet --version did not identify Kismet")

    help_output = run_command(
        ["kismetdb_dump_devices", "--help"], expected_returncodes={0, 1}
    )
    if "Kismetdb to JSON" not in help_output or "Input kismetdb file" not in help_output:
        raise SystemExit("kismetdb_dump_devices --help did not show expected usage text")

    negative_output = run_command(
        ["kismetdb_dump_devices"],
        expected_returncodes={1},
        expect_failure=True,
    )
    if "Expected --in" not in negative_output or "--out" not in negative_output:
        raise SystemExit("missing-input fault injection did not report required inputs")


if __name__ == "__main__":
    sys.exit(main())
