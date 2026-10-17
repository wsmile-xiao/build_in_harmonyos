#!/usr/bin/env python3
"""Functional consumer checks for the installed kakasi executable."""

import subprocess
import sys


def run(binary, args, data=b""):
    return subprocess.run(
        [binary] + args,
        input=data,
        check=False,
        capture_output=True,
    )


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <kakasi-binary>")

    binary = sys.argv[1]

    # 1. An unknown option makes kakasi print its version/usage banner to
    #    stderr and exit non-zero. Verify the packaged version string.
    probe = run(binary, ["-h"])
    banner = (probe.stdout or b"") + (probe.stderr or b"")
    if b"Version 2.3.6" not in banner:
        raise AssertionError(f"version banner not found: {banner!r}")

    # 2. Core Kanji -> Hiragana conversion in EUC-JP (no iconv required):
    #    "山" (EUC-JP b"\xbb\xb3") -> "やま" (EUC-JP b"\xa4\xe4\xa4\xde").
    #    "山" is a plain (non-okurigana) dictionary entry "やま 山".
    conv = run(binary, ["-JH", "-ieuc", "-oeuc"], data=b"\xbb\xb3")
    if conv.returncode != 0:
        raise AssertionError(
            f"kakasi -JH exited {conv.returncode}: {(conv.stderr or b'')!r}"
        )
    if conv.stdout != b"\xa4\xe4\xa4\xde":
        raise AssertionError(f"unexpected conversion output: {conv.stdout!r}")

    print("kakasi 2.3.6 consumer checks passed: version banner + Kanji->Hiragana")


if __name__ == "__main__":
    main()
