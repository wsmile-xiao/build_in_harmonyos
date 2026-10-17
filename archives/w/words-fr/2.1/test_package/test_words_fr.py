#!/usr/bin/env python3
"""Portable consumer check for the installed words-fr Conan data package."""
import argparse
import os
from pathlib import Path


def check(condition: bool, message: str, checks: list[str]) -> None:
    if not condition:
        raise AssertionError(message)
    checks.append(message)


def sort_key(word: str) -> tuple[bytes, bytes]:
    encoded = word.encode("utf-8")
    primary = bytearray()
    for value in encoded:
        if value == 32 or 48 <= value <= 57 or 65 <= value <= 90 or 97 <= value <= 122:
            primary.append(value + 32 if 65 <= value <= 90 else value)
    return bytes(primary), encoded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--word-list", type=Path)
    parser.add_argument("--expect-missing", action="store_true")
    args = parser.parse_args()

    checks: list[str] = []
    env_path = os.environ.get("WORDS_FR_FILE")
    path = args.word_list or (Path(env_path) if env_path else None)
    if args.expect_missing:
        check(path is None or not path.is_file(), "missing word-list rejected", checks)
        print("EXPECTED_MISSING_PATH_REJECTED")
        return 0
    check(path is not None, "WORDS_FR_FILE supplied by Conan run environment", checks)
    assert path is not None
    check(path.is_file(), f"word list exists: {path}", checks)
    data = path.read_bytes()
    check(bool(data), "word list is non-empty", checks)
    check(data.endswith(b"\n"), "word list ends with newline", checks)
    check(b"\r" not in data, "word list uses normalized LF newlines", checks)
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AssertionError(f"word list is not valid UTF-8: {exc}") from exc
    checks.append("word list decodes as strict UTF-8")
    words = text.splitlines()
    check(len(words) == 629569, f"entry count={len(words)}", checks)
    check(len(set(words)) == len(words), "entries are unique", checks)
    check(all(words), "entries contain no blank words", checks)
    check(all("/" not in word for word in words), "Aspell slash metadata is absent", checks)
    check(words == sorted(words, key=sort_key), "dictionary sort order is deterministic", checks)
    word_set = set(words)
    for sample in ("bonjour", "français", "éclair", "été"):
        check(sample in word_set, f"contains {sample}", checks)
    check("__words_fr_missing_test_marker__" not in word_set, "negative lookup misses", checks)
    check(path.name == "words-fr" and path.parts[-3:] == ("share", "dict", "words-fr"),
          "consumer path is share/dict/words-fr", checks)
    package_root = path.parents[2]
    for license_name in ("Copyright", "COPYING"):
        check((package_root / "licenses" / license_name).is_file(),
              f"package contains licenses/{license_name}", checks)
    print(f"WORDS_FR_CONSUMER_OK assertions={len(checks)} entries={len(words)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        raise SystemExit(f"WORDS_FR_CONSUMER_FAIL: {exc}")
