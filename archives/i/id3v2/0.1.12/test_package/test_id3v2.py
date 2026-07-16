#!/usr/bin/env python3
"""Functional test for the id3v2 binary: write an ID3 tag, read it back.

Exercises both id3v2 and the vendored id3lib: it tags a minimal MP3 with an
artist, then lists the tags and asserts the artist round-trips through the
TPE1 frame. Usage: python3 test_id3v2.py /path/to/id3v2
"""
import os
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) < 2:
        print("usage: test_id3v2.py <id3v2 binary>", file=sys.stderr)
        return 2
    id3v2 = sys.argv[1]

    workdir = tempfile.mkdtemp(prefix="id3v2_test_")
    mp3 = os.path.join(workdir, "sample.mp3")
    # Minimal MP3: one MPEG-1 Layer III frame header + zero padding. id3v2
    # prepends its ID3 tag regardless of the audio payload.
    with open(mp3, "wb") as fh:
        fh.write(b"\xff\xfb\x90\x00" + b"\x00" * 200)

    # 1. Version sanity — exercises binary startup and id3lib initialization.
    subprocess.run([id3v2, "--version"], check=True, stdout=subprocess.DEVNULL)

    # 2. Write an ID3 tag (artist) to the file.
    subprocess.run([id3v2, "--artist", "HarmonyTest", mp3],
                   check=True, stdout=subprocess.DEVNULL)

    # 3. Read it back — the artist must appear in the tag listing (TPE1 frame).
    listing = subprocess.run([id3v2, "-l", mp3], check=True,
                             capture_output=True, text=True)
    assert "HarmonyTest" in listing.stdout, (
        f"artist 'HarmonyTest' not found in tag listing:\n{listing.stdout}")

    print("id3v2 functional test passed (tag written and read back)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
