#!/usr/bin/env python3
"""Send one cross-compiled test executable to HarmonyOS and run it."""

import argparse
import os
import re
import subprocess
import sys


_REMOTE_PATH = re.compile(r"^/[A-Za-z0-9._/-]+$")
_LABEL = re.compile(r"^[A-Za-z0-9._-]+$")
_RC_MARKER = "__BOOST_NOOP_REMOTE_RC__="


def _invoke(command: list[str], timeout: int) -> subprocess.CompletedProcess:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=timeout,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result


def _hdc_prefix(executable: str, target: str) -> list[str]:
    command = [executable]
    if target:
        command.extend(["-t", target])
    return command


def run_target(
    hdc: str,
    target: str,
    remote_dir: str,
    label: str,
    executable: str,
    timeout: int,
) -> int:
    if not os.path.isfile(executable):
        raise ValueError(f"target executable does not exist: {executable}")
    if not _REMOTE_PATH.fullmatch(remote_dir):
        raise ValueError(f"unsafe remote directory: {remote_dir}")
    if not _LABEL.fullmatch(label):
        raise ValueError(f"unsafe target label: {label}")

    prefix = _hdc_prefix(hdc, target)
    remote_executable = f"{remote_dir}/{label}"
    commands = [
        [*prefix, "shell", f"mkdir -p {remote_dir}"],
        [*prefix, "file", "send", executable, remote_executable],
        [*prefix, "shell", f"chmod 755 {remote_executable}"],
        [
            *prefix,
            "shell",
            (
                f"cd {remote_dir}; ./{label}; rc=$?; "
                f"echo {_RC_MARKER}$rc; exit $rc"
            ),
        ],
    ]
    result = None
    for index, command in enumerate(commands):
        result = _invoke(command, timeout)
        if result.returncode != 0:
            return result.returncode
        combined_output = f"{result.stdout}\n{result.stderr}"
        if re.search(
            r"(?im)^\[(?:fail|f)\]|error opening file|no such file or directory",
            combined_output,
        ):
            print("HDC runner failed: HDC reported an operation error", file=sys.stderr)
            return 1
        if index == len(commands) - 1:
            matches = re.findall(
                rf"^{re.escape(_RC_MARKER)}(-?\d+)\s*$",
                result.stdout,
                flags=re.MULTILINE,
            )
            if len(matches) != 1:
                print("HDC runner failed: missing remote exit marker", file=sys.stderr)
                return 1
            remote_code = int(matches[0])
            return 0 if remote_code == 0 else remote_code
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hdc", required=True)
    parser.add_argument("--target", default="")
    parser.add_argument("--remote-dir", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("executable")
    args = parser.parse_args()
    try:
        return run_target(
            args.hdc,
            args.target,
            args.remote_dir,
            args.label,
            args.executable,
            args.timeout,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        print(f"HDC runner failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
