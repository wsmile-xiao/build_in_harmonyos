#!/usr/bin/env python3
"""Consumer checks for the platform-independent words data package."""

import sys
from pathlib import Path


DICTIONARIES = {
    "american-english",
    "british-english",
    "catala",
    "finnish",
    "french",
    "italian",
    "ngerman",
    "ogerman",
    "spanish",
}
EXPECTED_COUNTS = {
    "american-english": 123985,
    "british-english": 128005,
    "catala": 189057,
    "finnish": 88328,
    "french": 221377,
    "italian": 92034,
    "ngerman": 304736,
    "ogerman": 76258,
    "spanish": 56329,
}
ALIASES = {
    "british": "british-english",
    "catalan": "catala",
    "german": "ngerman",
    "usa": "american-english",
}
SAMPLES = {
    "american-english": ("color", "center"),
    "british-english": ("colour", "centre"),
    "catala": ("casa",),
    "finnish": ("kissa",),
    "french": ("bonjour",),
    "italian": ("ciao",),
    "ngerman": ("Haus",),
    "ogerman": ("Haus",),
    "spanish": ("hola",),
}
LICENSES = {
    "copyright-ca",
    "copyright-de",
    "copyright-de-doc",
    "copyright-en",
    "copyright-es",
    "copyright-fi",
    "copyright-fr",
    "copyright-it",
}


def dictionary_sort_key(word):
    """Model LC_ALL=C sort -df, including its bytewise tie-break."""
    encoded = word.encode("utf-8")
    primary = bytes(
        byte + 32 if 65 <= byte <= 90 else byte
        for byte in encoded
        if byte in b" abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    )
    return primary, encoded


def verify(package_root):
    dictionary_dir = Path(package_root) / "share" / "dict"
    actual_files = {path.name for path in dictionary_dir.iterdir() if path.is_file()}
    expected_files = DICTIONARIES | set(ALIASES)
    assert actual_files == expected_files, (
        f"dictionary files differ: missing={sorted(expected_files - actual_files)}, "
        f"extra={sorted(actual_files - expected_files)}"
    )

    contents = {}
    for name in sorted(DICTIONARIES):
        data = (dictionary_dir / name).read_bytes()
        text = data.decode("utf-8")
        words = text.splitlines()
        assert words and all(words), f"{name} is empty or contains blank entries"
        assert len(words) == EXPECTED_COUNTS[name], (
            f"{name} has {len(words)} entries, expected {EXPECTED_COUNTS[name]}"
        )
        assert all("/" not in word for word in words), f"{name} retains Aspell flags"
        assert words == sorted(words, key=dictionary_sort_key), f"{name} is not dictionary-sorted"
        assert len(words) == len(set(words)), f"{name} contains duplicate entries"
        contents[name] = (data, set(words))

    for name, expected_words in SAMPLES.items():
        words = contents[name][1]
        missing = sorted(set(expected_words) - words)
        assert not missing, f"{name} is missing expected words: {missing}"

    for alias, target in ALIASES.items():
        assert (dictionary_dir / alias).read_bytes() == contents[target][0], (
            f"{alias} does not match {target}"
        )

    license_dir = Path(package_root) / "licenses"
    licenses = list(license_dir.glob("copyright-*"))
    assert {path.name for path in licenses} == LICENSES, "upstream license files differ"
    assert all(path.stat().st_size for path in licenses), "an upstream copyright file is empty"

    print(
        f"validated {len(actual_files)} dictionary names, "
        f"{sum(len(words) for _, words in contents.values())} canonical entries, "
        f"and {len(licenses)} upstream copyright files"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_words.py <conan-package-folder>")
    verify(sys.argv[1])
