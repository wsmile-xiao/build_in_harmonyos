#!/usr/bin/env python3
"""Domain-level validation for the MBROLA Hungarian HU1 voice database."""

import argparse
import hashlib
import struct
import tempfile
from pathlib import Path


EXPECTED_DATABASE_SHA256 = (
    "fd18e03518c0cd58de82422c5a6661f1c2f894c396048167293591ed36444d0a"
)
EXPECTED_PHONES = {
    "2",
    "2:",
    "E",
    "J",
    "O",
    "S",
    "Z",
    "_",
    "a:",
    "b",
    "d",
    "d'",
    "dZ",
    "dz",
    "e:",
    "f",
    "g",
    "h",
    "i",
    "i:",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "o:",
    "p",
    "r",
    "s",
    "t",
    "t'",
    "tS",
    "ts",
    "u",
    "u:",
    "v",
    "y",
    "y:",
    "z",
}


class ValidationError(RuntimeError):
    pass


class Assertions:
    def __init__(self):
        self.count = 0

    def check(self, condition, description):
        if not condition:
            raise ValidationError(description)
        self.count += 1
        print(f"[PASS {self.count:02d}] {description}")


def _read_exact(data, offset, size):
    end = offset + size
    if end > len(data):
        raise ValidationError("truncated MBROLA database")
    return data[offset:end], end


def _read_zstring(data, offset):
    end = data.find(b"\0", offset, offset + 64)
    if end < 0:
        raise ValidationError("unterminated phoneme name")
    try:
        value = data[offset:end].decode("ascii")
    except UnicodeDecodeError as error:
        raise ValidationError("non-ASCII phoneme name") from error
    if not value:
        raise ValidationError("empty phoneme name")
    return value, end + 1


def parse_database(path):
    data = path.read_bytes()
    offset = 0

    magic, offset = _read_exact(data, offset, 6)
    if magic != b"MBROLA":
        raise ValidationError("invalid MBROLA magic")

    version_bytes, offset = _read_exact(data, offset, 5)
    version = version_bytes.decode("ascii")
    diphone_count = struct.unpack_from("<h", data, offset)[0]
    offset += 2
    old_pitch_mark_count = struct.unpack_from("<H", data, offset)[0]
    offset += 2
    if old_pitch_mark_count == 0:
        pitch_mark_count = struct.unpack_from("<i", data, offset)[0]
        offset += 4
    else:
        pitch_mark_count = old_pitch_mark_count
    raw_size = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    sample_rate = struct.unpack_from("<h", data, offset)[0]
    offset += 2
    period, coding = struct.unpack_from("<BB", data, offset)
    offset += 2

    pairs = set()
    inventory = set()
    pitch_marks_seen = 0
    raw_samples = 0
    physical_records = 0

    while pitch_marks_seen != pitch_mark_count:
        if physical_records >= diphone_count:
            raise ValidationError("diphone index ended before pitch marks")
        left, offset = _read_zstring(data, offset)
        right, offset = _read_zstring(data, offset)
        header, offset = _read_exact(data, offset, 4)
        half_segment, frame_count, wave_frame_count = struct.unpack(
            "<hBB", header
        )
        if half_segment < 0 or frame_count == 0 or wave_frame_count == 0:
            raise ValidationError("invalid diphone frame metadata")
        if coding != 1:
            raise ValidationError("HU1 is expected to use raw coding")

        pitch_marks_seen += frame_count
        raw_samples += wave_frame_count * period
        if pitch_marks_seen > pitch_mark_count:
            raise ValidationError("diphone index exceeds pitch-mark count")
        pairs.add((left, right))
        inventory.update((left, right))
        physical_records += 1

    for _ in range(physical_records, diphone_count):
        source_left, offset = _read_zstring(data, offset)
        source_right, offset = _read_zstring(data, offset)
        target_left, offset = _read_zstring(data, offset)
        target_right, offset = _read_zstring(data, offset)
        if (source_left, source_right) not in pairs:
            raise ValidationError("replacement references a missing diphone")
        pairs.add((target_left, target_right))
        inventory.update((target_left, target_right))

    return {
        "magic": magic,
        "version": version,
        "diphone_count": diphone_count,
        "pitch_mark_count": pitch_mark_count,
        "raw_size": raw_size,
        "sample_rate": sample_rate,
        "period": period,
        "coding": coding,
        "physical_records": physical_records,
        "pitch_marks_seen": pitch_marks_seen,
        "raw_samples": raw_samples,
        "pairs": pairs,
        "inventory": inventory,
    }


def parse_pho(path):
    segments = []
    pitch_targets = 0
    comment_lines = 0

    for line_number, raw_line in enumerate(
        path.read_text(encoding="latin-1").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(";"):
            comment_lines += 1
            continue

        fields = line.split()
        if len(fields) < 2:
            raise ValidationError(f"line {line_number}: missing duration")
        phone = fields[0]
        try:
            duration = int(fields[1])
        except ValueError as error:
            raise ValidationError(
                f"line {line_number}: invalid duration"
            ) from error
        if duration <= 0:
            raise ValidationError(f"line {line_number}: nonpositive duration")

        pitch_fields = fields[2:]
        if len(pitch_fields) % 2:
            raise ValidationError(
                f"line {line_number}: unpaired pitch target"
            )
        for index in range(0, len(pitch_fields), 2):
            try:
                position = float(pitch_fields[index])
                frequency = float(pitch_fields[index + 1])
            except ValueError as error:
                raise ValidationError(
                    f"line {line_number}: invalid pitch target"
                ) from error
            if not 0 <= position <= 100 or frequency <= 0:
                raise ValidationError(
                    f"line {line_number}: pitch target out of range"
                )
            pitch_targets += 1

        segments.append((phone, duration))

    if not segments:
        raise ValidationError("PHO fixture has no segments")
    return {
        "segments": segments,
        "pitch_targets": pitch_targets,
        "comment_lines": comment_lines,
    }


def expect_validation_error(function, path):
    try:
        function(path)
    except ValidationError:
        return True
    return False


def validate(database_path, pho_path, readme_path, license_path):
    assertions = Assertions()
    database = parse_database(database_path)
    fixture = parse_pho(pho_path)

    assertions.check(
        database["magic"] == b"MBROLA" and database["version"] == "2.069",
        "database magic and format version match HU1",
    )
    assertions.check(
        database["diphone_count"] == 1596
        and database["pitch_mark_count"] == 43239,
        "header declares 1596 diphones and 43239 pitch marks",
    )
    assertions.check(
        database["sample_rate"] == 16000
        and database["period"] == 100
        and database["coding"] == 1,
        "audio parameters are 16 kHz, period 100, raw coding",
    )
    assertions.check(
        database["physical_records"] == 1596
        and len(database["pairs"]) == 1596,
        "all 1596 diphone index records parse uniquely",
    )
    assertions.check(
        database["pitch_marks_seen"] == database["pitch_mark_count"]
        and database["raw_samples"] * 2 == database["raw_size"],
        "pitch-mark and waveform frame accounting is exact",
    )
    assertions.check(
        database["inventory"] == EXPECTED_PHONES,
        "database exposes the expected 40-phone Hungarian inventory",
    )
    assertions.check(
        ("_", "_") in database["pairs"],
        "database contains the required silence diphone",
    )
    assertions.check(
        hashlib.sha256(database_path.read_bytes()).hexdigest()
        == EXPECTED_DATABASE_SHA256,
        "installed HU1 database matches the authoritative source payload",
    )

    segments = fixture["segments"]
    fixture_phones = {phone for phone, _ in segments}
    transitions = list(
        zip(
            (phone for phone, _ in segments),
            (phone for phone, _ in segments[1:]),
        )
    )
    assertions.check(
        len(segments) == 598,
        "kisk1.pho contains 598 synthesis segments",
    )
    assertions.check(
        len(transitions) == 597,
        "kisk1.pho defines 597 adjacent phoneme transitions",
    )
    assertions.check(
        fixture["pitch_targets"] == 158,
        "kisk1.pho contains 158 paired pitch targets",
    )
    assertions.check(
        sum(duration for _, duration in segments) == 53260,
        "kisk1.pho has the expected total duration",
    )
    assertions.check(
        fixture_phones <= database["inventory"],
        "every fixture phoneme belongs to the HU1 inventory",
    )
    assertions.check(
        all(pair in database["pairs"] for pair in transitions),
        "all 597 fixture transitions resolve to HU1 diphones",
    )

    license_text = license_path.read_text(
        encoding="latin-1"
    ).lower()
    assertions.check(
        "only with the mbrola program" in license_text
        and "may not be sold" in license_text
        and "this notice is copied and distributed with it" in license_text,
        "bundled license retains use, sale, and redistribution restrictions",
    )
    readme_text = readme_path.read_text(encoding="latin-1").lower()
    assertions.check(
        "hu1 1.002" in readme_text
        and "mbrola hu1 test/kisk1.pho kisk1.wav" in readme_text,
        "bundled README documents the release and synthesis example",
    )

    with tempfile.TemporaryDirectory(prefix="mbrola-hu1-test-") as temp_dir:
        corrupt_database = Path(temp_dir) / "corrupt-hu1"
        corrupt_database.write_bytes(
            b"XBROLA" + database_path.read_bytes()[6:64]
        )
        assertions.check(
            expect_validation_error(parse_database, corrupt_database),
            "corrupt MBROLA magic is rejected",
        )

        malformed_pho = Path(temp_dir) / "malformed.pho"
        malformed_pho.write_text("_ 100 50\n", encoding="ascii")
        assertions.check(
            expect_validation_error(parse_pho, malformed_pho),
            "unpaired PHO pitch target is rejected",
        )

    if assertions.count != 18:
        raise ValidationError(
            f"expected 18 assertions, executed {assertions.count}"
        )
    print("mbrola-hu1: 18/18 semantic assertions passed")


def main():
    parser = argparse.ArgumentParser()
    roots = parser.add_mutually_exclusive_group(required=True)
    roots.add_argument("--source-root", type=Path)
    roots.add_argument("--package-root", type=Path)
    arguments = parser.parse_args()

    if arguments.source_root:
        root = arguments.source_root
        database_path = root / "hu1"
        pho_path = root / "test" / "kisk1.pho"
        readme_path = root / "README.txt"
        license_path = root / "license.txt"
    else:
        root = arguments.package_root
        database_path = root / "share" / "mbrola" / "hu1" / "hu1"
        documentation = root / "share" / "doc" / "mbrola-hu1"
        pho_path = documentation / "examples" / "kisk1.pho"
        readme_path = documentation / "README.txt"
        license_path = root / "licenses" / "license.txt"

    for required_path in (
        database_path,
        pho_path,
        readme_path,
        license_path,
    ):
        if not required_path.is_file():
            raise ValidationError(f"required package artifact missing: {required_path}")

    validate(database_path, pho_path, readme_path, license_path)


if __name__ == "__main__":
    main()
