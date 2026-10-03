#!/usr/bin/env python3
"""Generate redistributable synthetic fixtures for upstream check programs."""
import os
import struct


def generate(directory):
    os.makedirs(directory, exist_ok=True)
    entries = [
        (b"computer", b"{\\rtf1 komputer}"),
        (b"shield", b"{\\rtf1 tarcza}"),
        (b"s\xb3owo", b"{\\rtf1 definicja s\xb3owa}"),
    ]
    for number in (100, 101, 200, 201):
        prefix = os.path.join(directory, "dict{}".format(number))
        with open(prefix + ".idx", "wb") as idx, open(prefix + ".dat", "wb") as dat:
            idx.write(struct.pack("<LLHHLL236s", 0x8D4E11D5, 0, len(entries), 0, 0, 256, b""))
            for ordinal, (word, definition) in enumerate(entries, 1):
                idx.write(struct.pack("<BBHL", len(word) + 1, 2, ordinal, dat.tell()))
                idx.write(word + b"\0")
                dat.write(struct.pack("<L", len(definition)) + definition)
