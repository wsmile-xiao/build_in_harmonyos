#!/usr/bin/env python3
"""Exercise cutmp3 metadata parsing, cutting, and error handling."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(runner, *arguments, cwd=None, env=None):
    return subprocess.run(
        [*runner, *arguments],
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def make_mp3(path):
    header = bytes.fromhex("fffb90c0")
    frame = header + bytes(417 - len(header))
    path.write_bytes(frame * 100)


def main():
    runner = sys.argv[1:]
    check(bool(runner), "missing cutmp3 command")

    with tempfile.TemporaryDirectory(
        prefix="cutmp3-functional-", dir=os.environ.get("TMPDIR")
    ) as directory:
        work = Path(directory)
        source = work / "input.mp3"
        output = work / "output.mp3"
        invalid = work / "invalid.mp3"
        make_mp3(source)
        invalid.write_bytes(b"not an MPEG audio stream")

        help_result = run(runner, "-h", cwd=work)
        check(help_result.returncode == 0, "help command failed")
        check("cutmp3  version 4.0" in help_result.stdout, "version missing")
        check("Usage:  cutmp3" in help_result.stdout, "usage missing")

        info_result = run(runner, "-I", str(source), cwd=work)
        check(info_result.returncode == 0, "metadata inspection failed")
        check("MPEG1-Layer3" in info_result.stdout, "MPEG format not detected")
        check("44100 Hz Mono" in info_result.stdout, "audio properties differ")

        cut_result = run(
            runner,
            "-i",
            str(source),
            "-a",
            "0:00",
            "-b",
            "0:01",
            "-O",
            str(output),
            cwd=work,
        )
        check(cut_result.returncode == 0, "one-second cut failed")
        check("saved 0:00.00 - 0:01.00" in cut_result.stdout, "cut not reported")
        check(output.is_file(), "cut output was not created")
        check(0 < output.stat().st_size < source.stat().st_size, "cut size invalid")

        output_info = run(runner, "-I", str(output), cwd=work)
        check(output_info.returncode == 0, "cut output cannot be parsed")
        check("MPEG1-Layer3" in output_info.stdout, "cut output format invalid")

        raw_info = run(runner, "-F", "-I", str(source), cwd=work)
        check(raw_info.returncode == 0, "raw metadata inspection failed")
        check(len(raw_info.stdout.split()) >= 6, "raw metadata fields missing")

        invalid_result = run(runner, "-I", str(invalid), cwd=work)
        check(invalid_result.returncode != 0, "invalid input was accepted")

    print("cutmp3 functional assertions: 15 passed")


if __name__ == "__main__":
    main()
