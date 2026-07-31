#!/usr/bin/env python3
"""Semantic consumer validation for an installed MBROLA GR2 voice package."""

from __future__ import annotations

import struct
import sys
from pathlib import Path


EXPECTED_PHONEMES = {
    "C", "D", "G", "L", "M", "N", "R", "S", "T", "V", "X", "Y", "Z",
    "_", "a", "b", "c", "d", "e", "f", "g", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "x", "z",
}


class Checks:
    def __init__(self) -> None:
        self.count = 0

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            raise AssertionError(message)
        self.count += 1


def read_zstring(data: bytes, position: int) -> tuple[str, int]:
    end = data.find(b"\0", position)
    if end < 0:
        raise AssertionError("unterminated phoneme name in diphone index")
    return data[position:end].decode("ascii"), end + 1


def parse_database(data: bytes) -> dict:
    position = 11
    diphone_count = struct.unpack_from("<H", data, position)[0]
    position += 2
    old_pitch_count = struct.unpack_from("<H", data, position)[0]
    position += 2
    if old_pitch_count == 0:
        pitch_count = struct.unpack_from("<I", data, position)[0]
        position += 4
    else:
        pitch_count = old_pitch_count

    raw_size = struct.unpack_from("<I", data, position)[0]
    position += 4
    sample_rate = struct.unpack_from("<H", data, position)[0]
    position += 2
    period = data[position]
    coding = data[position + 1]
    position += 2

    pairs: list[tuple[str, str]] = []
    frame_count = 0
    for _ in range(diphone_count):
        left, position = read_zstring(data, position)
        right, position = read_zstring(data, position)
        struct.unpack_from("<H", data, position)[0]
        frames = data[position + 2]
        position += 4
        pairs.append((left, right))
        frame_count += frames

    pitch_bytes = (pitch_count + 3) // 4
    raw_offset = position + pitch_bytes
    raw_end = raw_offset + raw_size
    return {
        "magic": data[:6],
        "version": data[6:11].decode("ascii"),
        "diphone_count": diphone_count,
        "pitch_count": pitch_count,
        "raw_size": raw_size,
        "sample_rate": sample_rate,
        "period": period,
        "coding": coding,
        "pairs": pairs,
        "frame_count": frame_count,
        "raw_offset": raw_offset,
        "raw_end": raw_end,
        "metadata": data[raw_end:],
    }


def parse_pho(path: Path) -> tuple[list[str], list[int]]:
    phonemes: list[str] = []
    durations: list[int] = []
    text = path.read_bytes().replace(b"\0", b"").decode("ascii")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        fields = line.split()
        phonemes.append(fields[0])
        durations.append(int(fields[1]))
        pitch_fields = fields[2:]
        if len(pitch_fields) % 2:
            raise AssertionError(f"unpaired pitch position/value fields: {line}")
        for value in pitch_fields:
            int(value)
    return phonemes, durations


def main(package_root: str) -> int:
    checks = Checks()
    root = Path(package_root)
    voice_dir = root / "share" / "mbrola" / "gr2"
    database_path = voice_dir / "gr2"
    pho_path = voice_dir / "TEST" / "DEMOST~1.PHO"
    readme_path = root / "share" / "doc" / "mbrola-gr2" / "README.txt"
    license_path = root / "licenses" / "license.txt"

    data = database_path.read_bytes()
    checks.require(len(data) > 6_000_000, "GR2 database is unexpectedly small")

    database = parse_database(data)
    checks.require(database["magic"] == b"MBROLA", "invalid MBROLA magic")
    checks.require(database["version"] == "2.060", "unexpected database format")
    checks.require(database["diphone_count"] == 1081, "unexpected diphone count")
    checks.require(database["pitch_count"] == 19597, "unexpected pitch-mark count")
    checks.require(database["raw_size"] == 6608960, "unexpected raw sample size")
    checks.require(database["sample_rate"] == 22050, "unexpected sample rate")
    checks.require(database["period"] == 160, "unexpected MBROLA period")
    checks.require(database["coding"] == 1, "unexpected MBROLA sample coding")

    pairs = database["pairs"]
    pair_set = set(pairs)
    phoneme_set = {phoneme for pair in pairs for phoneme in pair}
    checks.require(len(pairs) == 1081, "diphone index was not fully parsed")
    checks.require(len(pair_set) == 1081, "duplicate diphone index entry")
    checks.require(
        database["frame_count"] == database["pitch_count"],
        "diphone frame total does not match pitch-mark count",
    )
    checks.require(phoneme_set == EXPECTED_PHONEMES, "unexpected phoneme inventory")
    checks.require(pairs[-1] == ("_", "_"), "silence diphone is not final")
    checks.require(
        database["raw_offset"] < database["raw_end"] <= len(data),
        "raw sample region exceeds database bounds",
    )
    checks.require(
        b"GR2 male Hellenic(Greek) voice" in database["metadata"],
        "embedded GR2 identity metadata is missing",
    )

    phonemes, durations = parse_pho(pho_path)
    checks.require(len(phonemes) == 211, "unexpected PHO command count")
    checks.require(not (set(phonemes) - phoneme_set), "PHO uses unknown phonemes")
    checks.require(
        all(pair in pair_set for pair in zip(phonemes, phonemes[1:])),
        "PHO uses a diphone transition absent from GR2",
    )
    checks.require(all(duration > 0 for duration in durations), "invalid PHO duration")

    readme = readme_path.read_text(encoding="latin-1")
    checks.require("It consists of 1081 diphones." in readme, "README count mismatch")
    license_text = license_path.read_text(encoding="ascii")
    checks.require(
        "only with  the Mbrola program" in license_text,
        "voice-specific MBROLA use condition is missing",
    )
    checks.require(
        "this notice is copied and distributed with it" in license_text,
        "redistribution notice condition is missing",
    )

    print(
        f"mbrola-gr2 semantic consumer validation: "
        f"{checks.count}/{checks.count} assertions passed; "
        f"{len(pair_set)} diphones; {len(phonemes)} PHO commands"
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_mbrola_voice.py <package-root>")
    raise SystemExit(main(sys.argv[1]))
