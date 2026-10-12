#!/usr/bin/env python3
"""Exercise the installed WeeChat binaries without an interactive terminal."""

import os
import pathlib
import re
import subprocess
import sys


PLUGIN_NAMES = [
    "alias",
    "buflist",
    "charset",
    "exec",
    "fifo",
    "fset",
    "irc",
    "logger",
    "relay",
    "script",
    "trigger",
    "typing",
    "xfer",
]


def run_checked(command, env=None, timeout=120):
    result = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        env=env,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {command!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout, result.stderr


def main():
    package_folder = pathlib.Path(sys.argv[1]).resolve()
    workdir = pathlib.Path(sys.argv[2]).resolve()
    curses = package_folder / "bin" / "weechat"
    headless = package_folder / "bin" / "weechat-headless"
    for binary in (curses, headless):
        if not binary.is_file():
            raise SystemExit(f"missing binary: {binary}")

    # no LD_LIBRARY_PATH: the packaged binaries must resolve their shared
    # dependencies through their own RPATH
    standalone_env = os.environ.copy()
    standalone_env.pop("LD_LIBRARY_PATH", None)

    results = []

    def run_case(name, func):
        try:
            detail = func()
        except Exception as exc:  # noqa: BLE001 - report and continue
            results.append(False)
            print(f"[FAIL] {name}: {exc}")
        else:
            results.append(True)
            print(f"[PASS] {name}" + (f": {detail}" if detail else ""))

    def case_version(binary):
        def check():
            stdout, _ = run_checked(
                [str(binary), "--version"], env=standalone_env, timeout=60
            )
            version = stdout.strip()
            if version != "4.9.4":
                raise AssertionError(f"unexpected version output: {version!r}")
            return version

        return check

    def case_help():
        stdout, _ = run_checked(
            [str(headless), "--help"], env=standalone_env, timeout=60
        )
        if "--run-command" not in stdout:
            raise AssertionError("--run-command missing from --help output")
        return "headless options listed"

    def case_plugins():
        home = workdir / "weechat-home"
        home.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["WEECHAT_EXTRA_LIBDIR"] = str(package_folder / "lib" / "weechat")
        stdout, stderr = run_checked(
            [
                str(headless),
                "--stdout",
                "-d",
                str(home),
                "-r",
                "/plugin list",
                "-r",
                "/quit",
            ],
            env=env,
            timeout=180,
        )
        combined = stdout + stderr
        missing = [
            name
            for name in PLUGIN_NAMES
            if not re.search(rf"\b{re.escape(name)}\b", combined)
        ]
        if missing:
            raise AssertionError(
                f"plugins missing from /plugin list: {missing}\n"
                f"stdout:\n{stdout}\nstderr:\n{stderr}"
            )
        return f"{len(PLUGIN_NAMES)} plugins listed"

    run_case("curses binary version", case_version(curses))
    run_case("headless binary version", case_version(headless))
    run_case("headless help options", case_help)
    run_case("headless plugin loading", case_plugins)

    passed = sum(1 for ok in results if ok)
    failed = len(results) - passed
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    if failed:
        raise SystemExit(1)
    print("weechat consumer test passed: versions, help, and plugin loading")


if __name__ == "__main__":
    main()
