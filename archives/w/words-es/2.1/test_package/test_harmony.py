#!/usr/bin/env python3
"""Run the words-es consumer on a connected HarmonyOS PC emulator using hdc."""

import argparse
import subprocess
import uuid
from pathlib import Path


def run(arguments):
    result = subprocess.run(
        arguments,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hdc", required=True, type=Path)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--word-list", required=True, type=Path)
    parser.add_argument("--expected-machine", default="x86_64")
    arguments = parser.parse_args()

    hdc = str(arguments.hdc.resolve())
    binary = arguments.binary.resolve()
    word_list = arguments.word_list.resolve()
    if not binary.is_file() or not word_list.is_file():
        parser.error("--binary and --word-list must point to existing files")

    targets = [line for line in run([hdc, "list", "targets"]).splitlines() if line]
    if len(targets) != 1:
        parser.error(f"expected exactly one connected hdc target, found {targets}")

    machine = run([hdc, "shell", "uname", "-m"])
    if machine != arguments.expected_machine:
        raise SystemExit(
            f"expected HarmonyOS machine {arguments.expected_machine}, got {machine}"
        )

    remote_dir = f"/data/local/tmp/words-es-2.1-{uuid.uuid4().hex}"
    remote_binary = f"{remote_dir}/test_words_es"
    remote_list = f"{remote_dir}/words-es"
    run([hdc, "shell", "mkdir", "-p", remote_dir])
    try:
        run([hdc, "file", "send", str(binary), remote_binary])
        run([hdc, "file", "send", str(word_list), remote_list])
        run([hdc, "shell", "chmod", "700", remote_binary])
        command = (
            f"WORDS_ES_FILE={remote_list} {remote_binary} --require-ohos "
            f"--expect-machine={arguments.expected_machine} --expect-count=56329"
        )
        output = run([hdc, "shell", "sh", "-c", command])
        if "HARMONYOS_TEST_OK" not in output:
            raise SystemExit(f"HarmonyOS consumer did not report success: {output}")
        print(output)
    finally:
        run([hdc, "shell", "rm", "-rf", remote_dir])


if __name__ == "__main__":
    main()
