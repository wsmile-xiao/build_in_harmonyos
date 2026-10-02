#!/usr/bin/env python3
"""Command-line contract of the packaged `tanidvr` DVR client.

    test_tanidvr.py --tanidvr <tanidvr command>
"""

import subprocess
import sys


def split_commands(argv):
    """Split "--tanidvr <tokens...>" (emulator flags may live in the prefix)."""
    tokens = argv[argv.index("--tanidvr") + 1:] if "--tanidvr" in argv else []
    return tokens


COMMAND = split_commands(sys.argv[1:])
if not COMMAND:
    sys.exit("usage: test_tanidvr.py --tanidvr <cmd>")

passed = []


def check(condition, message):
    if not condition:
        print(f"FAIL: {message}")
        sys.exit(1)
    passed.append(message)
    print(f"ok: {message}")


def run(*args, stdin=None):
    return subprocess.run(
        [*COMMAND, *args],
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )


help_result = run("-h")
help_text = help_result.stdout.decode("utf-8", "replace")
help_err = help_result.stderr.decode("utf-8", "replace")

check(help_result.returncode == 0, "tanidvr -h exits with 0")
check("TaniDVR 1.4.1" in help_text, "tanidvr -h reports the packaged version")
check(
    "Usage: tanidvr <-m <mode>>" in help_text,
    "tanidvr -h prints the upstream usage synopsis",
)
check(
    "--operation-mode" in help_text and "--dvr-channel" in help_text,
    "tanidvr -h documents the long options",
)
check(
    "GNU General Public License" in help_text,
    "tanidvr -h prints the GPL notice",
)
check(help_err == "", "tanidvr -h keeps stderr clean")

no_args = run()
no_args_err = no_args.stderr.decode("utf-8", "replace")
check(no_args.returncode != 0, "tanidvr without arguments fails")
check(
    "It is required to define an operation mode." in no_args_err,
    "tanidvr without arguments reports the missing operation mode",
)

mode_only = run("-m", "0")
mode_only_err = mode_only.stderr.decode("utf-8", "replace")
check(mode_only.returncode != 0, "tanidvr -m without a target fails")
check(
    "It is required to define a DVR target." in mode_only_err,
    "tanidvr -m without a target reports the missing DVR address",
)

bad_option = run("--no-such-option")
bad_option_err = bad_option.stderr.decode("utf-8", "replace")
check(bad_option.returncode != 0, "tanidvr rejects an unknown long option")
check(
    "unrecognized option" in bad_option_err,
    "tanidvr reports the unknown option through getopt_long",
)

bad_mode = run("-m", "99", "-t", "127.0.0.1", "-u", "admin", "-w", "secret")
bad_mode_err = bad_mode.stderr.decode("utf-8", "replace")
check(bad_mode.returncode != 0, "tanidvr rejects an out-of-range operation mode")
check(
    "Invalid operation mode." in bad_mode_err,
    "tanidvr validates the -m argument",
)

print(f"test_tanidvr.py: {len(passed)} assertions passed")
