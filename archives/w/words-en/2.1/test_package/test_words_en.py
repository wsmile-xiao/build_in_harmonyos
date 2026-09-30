#!/usr/bin/env python3
"""Consumer checks for the packaged American English word list."""

import argparse
import hashlib
import os
from pathlib import Path
import sys

EXPECTED_ENTRIES = 123115
EXPECTED_SHA256 = "7316ff93a3dc147ce54d1bde684aa4d321f86f40d008702b9c948a4ff21e7889"
US_WORDS = ("color", "center", "organize", "theater")
BRITISH_ONLY_WORDS = ("colour", "centre", "organise")


def fail(message):
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--harmony", action="store_true")
    parser.add_argument("--expect-missing")
    parser.add_argument("word_file", nargs="?")
    args = parser.parse_args()

    if args.expect_missing:
        if Path(args.expect_missing).exists():
            return fail("the missing-file scenario unexpectedly found a file")
        print("missing word-list path rejected")
        return 0

    word_file = args.word_file or os.environ.get("WORDS_EN_FILE")
    if not word_file:
        return fail("WORDS_EN_FILE is unset and no word-list path was provided")

    if args.harmony:
        if not hasattr(os, "uname"):
            return fail("HarmonyOS identity cannot be checked on this runtime")
        system = os.uname()
        if system.sysname != "HarmonyOS" or system.machine != "aarch64":
            return fail(
                f"expected HarmonyOS/aarch64, got {system.sysname}/{system.machine}"
            )

    path = Path(word_file)
    if not path.is_file():
        return fail(f"word-list file is missing: {path}")
    try:
        data = path.read_bytes()
        words = data.decode("utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        return fail(f"word-list file is unreadable or not UTF-8: {error}")

    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        return fail(f"unexpected word-list content SHA256: {digest}")
    if len(words) != EXPECTED_ENTRIES:
        return fail(f"expected {EXPECTED_ENTRIES} words, found {len(words)}")
    if not words or any(not word for word in words):
        return fail("word list contains an empty entry")
    if len(set(words)) != len(words):
        return fail("word list contains duplicate entries")
    if any(word not in words for word in US_WORDS):
        return fail("one or more expected American spellings are absent")
    if any(word in words for word in BRITISH_ONLY_WORDS):
        return fail("British-only spellings leaked into the American list")

    runtime = "HarmonyOS 6.0/aarch64" if args.harmony else sys.platform
    print(f"words-en consumer checks passed ({runtime}; {len(words)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
