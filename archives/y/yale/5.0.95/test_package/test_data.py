#!/usr/bin/env python3
"""Consumer checks for the unmodified CDS V/50 Yale Bright Star Catalog."""

import argparse
import gzip
import hashlib
import os
import platform
import sys
from pathlib import Path


EXPECTED_FILES = {
    "catalog.gz": (
        573921,
        "3dc44b1e90be8fbe5bcc7656032560f51275f985c7e3f783c9028e1838ec7bed",
    ),
    "notes.gz": (
        161634,
        "d489d8ceaead65b0af8bce36f2421886782bbe953ecf76b08bc3fd4b84df1405",
    ),
    "ReadMe": (
        11571,
        "44fd9c73e2eecad0beb47bdfa3f01c60fd43f93d6964198e31fcd48732de5b33",
    ),
}
EXPECTED_CATEGORIES = {"C", "D", "DYN", "G", "M", "N", "P", "R", "RV", "S", "SB", "VAR"}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def data_directory():
    value = os.environ.get("YALE_BSC5_DIR")
    require(value, "Conan run environment did not define YALE_BSC5_DIR")
    directory = Path(value)
    require(directory.is_dir(), f"Yale data directory is missing: {directory}")
    return directory


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scan_catalog(directory):
    count = 0
    coordinate_count = 0
    visual_magnitude_count = 0
    sirius = None
    with gzip.open(directory / "catalog.gz", "rb") as stream:
        for raw in stream:
            row = raw.rstrip(b"\r\n")
            require(160 <= len(row) <= 197, f"invalid catalog row width {len(row)}")
            row.decode("ascii")
            fields = row.ljust(197, b" ")
            hr = int(fields[0:4].decode("ascii"))
            count += 1
            require(hr == count, f"catalog HR sequence breaks at record {count}: {hr}")

            visual_magnitude = fields[102:107].strip()
            if visual_magnitude:
                float(visual_magnitude.decode("ascii"))
                visual_magnitude_count += 1

            coordinates = fields[75:90]
            if coordinates.strip():
                ra_hours = int(fields[75:77])
                ra_minutes = int(fields[77:79])
                ra_seconds = float(fields[79:83])
                dec_sign = fields[83:84]
                dec_degrees = int(fields[84:86])
                dec_minutes = int(fields[86:88])
                dec_seconds = int(fields[88:90])
                require(0 <= ra_hours <= 23, f"invalid J2000 RA hour at HR {hr}")
                require(0 <= ra_minutes <= 59, f"invalid J2000 RA minute at HR {hr}")
                require(0.0 <= ra_seconds <= 60.0, f"invalid J2000 RA second at HR {hr}")
                require(dec_sign in (b"+", b"-"), f"invalid J2000 Dec sign at HR {hr}")
                require(0 <= dec_degrees <= 90, f"invalid J2000 Dec degree at HR {hr}")
                require(0 <= dec_minutes <= 59, f"invalid J2000 Dec minute at HR {hr}")
                require(0 <= dec_seconds <= 60, f"invalid J2000 Dec second at HR {hr}")
                coordinate_count += 1

            if hr == 2491:
                sirius = (fields[4:14].decode("ascii").strip(), visual_magnitude)

    require(count == 9110, f"expected 9110 catalog records, found {count}")
    require(coordinate_count == 9096, f"expected 9096 populated J2000 coordinates, found {coordinate_count}")
    require(visual_magnitude_count == 9096, f"expected 9096 visual magnitudes, found {visual_magnitude_count}")
    require(sirius == ("9Alp CMa", b"-1.46"), f"HR 2491 Sirius record mismatch: {sirius!r}")
    return count


def scan_notes(directory):
    count = 0
    previous_hr = 0
    categories = set()
    with gzip.open(directory / "notes.gz", "rb") as stream:
        for raw in stream:
            row = raw.rstrip(b"\r\n")
            require(15 <= len(row) <= 132, f"invalid notes row width {len(row)}")
            row.decode("ascii")
            fields = row.ljust(132, b" ")
            hr = int(fields[1:5].decode("ascii"))
            note_number = int(fields[5:7].decode("ascii"))
            category = fields[7:11].decode("ascii").strip().rstrip(":")
            require(1 <= hr <= 9110, f"notes HR out of range: {hr}")
            require(hr >= previous_hr, f"notes are not ordered by HR at record {count + 1}")
            require(category in EXPECTED_CATEGORIES, f"unknown notes category: {category!r}")
            require(bool(fields[12:].strip()), f"empty remark for HR {hr}")
            require(1 <= note_number <= 99, f"invalid note counter for HR {hr}: {note_number}")
            categories.add(category)
            previous_hr = hr
            count += 1

    require(count == 9190, f"expected 9190 notes records, found {count}")
    require(categories == EXPECTED_CATEGORIES, f"unexpected category inventory: {sorted(categories)}")
    return count


def test_resource_inventory_and_original_bytes():
    directory = data_directory()
    actual_names = {entry.name for entry in directory.iterdir() if entry.is_file()}
    require(actual_names == set(EXPECTED_FILES), f"installed resource set differs: {sorted(actual_names)}")
    for name, (expected_size, expected_digest) in EXPECTED_FILES.items():
        path = directory / name
        require(path.stat().st_size == expected_size, f"unexpected size for {name}")
        require(file_sha256(path) == expected_digest, f"original bytes changed for {name}")


def test_catalog_consumer():
    count = scan_catalog(data_directory())
    print(f"  consumed {count} fixed-width star records")


def test_notes_consumer():
    count = scan_notes(data_directory())
    print(f"  consumed {count} remark records across {len(EXPECTED_CATEGORIES)} categories")


def test_readme_consumer():
    readme = (data_directory() / "ReadMe").read_text(encoding="ascii")
    for text in ("Hoffleit", "Warren", "9110", "9190", "catalog", "notes"):
        require(text in readme, f"upstream ReadMe lacks expected source detail: {text}")


def test_harmonyos_aarch64_consumer():
    system = platform.system()
    machine = platform.machine().lower()
    require(system == "HarmonyOS", f"expected HarmonyOS target, detected {system}")
    require(machine == "aarch64", f"expected aarch64 target, detected {machine}")
    directory = data_directory()
    catalog_records = scan_catalog(directory)
    notes_records = scan_notes(directory)
    print(f"  HarmonyOS aarch64 streamed installed data: {catalog_records} stars, {notes_records} notes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-ohos",
        action="store_true",
        help="also require HarmonyOS/aarch64 and repeat the installed-data consumer scan",
    )
    args = parser.parse_args()

    tests = [
        ("resource inventory and byte integrity", test_resource_inventory_and_original_bytes),
        ("catalog fixed-width consumer", test_catalog_consumer),
        ("notes fixed-width consumer", test_notes_consumer),
        ("upstream ReadMe consumer", test_readme_consumer),
    ]
    if args.require_ohos:
        tests.append(("HarmonyOS aarch64 installed-data consumer", test_harmonyos_aarch64_consumer))

    passed = 0
    for name, test in tests:
        try:
            test()
        except Exception as exc:
            print(f"FAIL: {name}: {exc}", file=sys.stderr)
            raise
        passed += 1
        print(f"PASS: {name}")
    print(f"YALE_TESTS_PASS ({passed}/{len(tests)})")


if __name__ == "__main__":
    main()
