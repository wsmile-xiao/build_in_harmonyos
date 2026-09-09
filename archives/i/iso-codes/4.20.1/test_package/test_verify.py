#!/usr/bin/env python3
"""Validate the complete installed iso-codes 4.20.1 data contract."""

import json
import os
import pathlib
import sys
import xml.etree.ElementTree as element_tree


DOMAINS = (
    "iso_15924",
    "iso_3166-1",
    "iso_3166-2",
    "iso_3166-3",
    "iso_4217",
    "iso_639-2",
    "iso_639-3",
    "iso_639-5",
)
DATA_KEYS = {domain: domain.removeprefix("iso_") for domain in DOMAINS}
XML_ALIASES = {
    "iso_639.xml": "iso_639-2.xml",
    "iso_639_3.xml": "iso_639-3.xml",
    "iso_639_5.xml": "iso_639-5.xml",
    "iso_3166_2.xml": "iso_3166-2.xml",
    "iso_3166.xml": "iso_3166-1.xml",
}
XML_ROOTS = {
    "iso_15924": "iso_15924_entries",
    "iso_3166-1": "iso_3166_entries",
    "iso_3166-2": "iso_3166_2_entries",
    "iso_3166-3": "iso_3166_3_entries",
    "iso_4217": "iso_4217_entries",
    "iso_639-2": "iso_639_entries",
    "iso_639-3": "iso_639_3_entries",
    "iso_639-5": "iso_639_5_entries",
}
XML_ENTRY_TAGS = {
    "iso_15924": "iso_15924_entry",
    "iso_3166-1": "iso_3166_entry",
    "iso_3166-2": "iso_3166_2_entry",
    "iso_3166-3": "iso_3166_3_entry",
    "iso_4217": "iso_4217_entry",
    "iso_639-2": "iso_639_entry",
    "iso_639-3": "iso_639_3_entry",
    "iso_639-5": "iso_639_5_entry",
}
MO_MAGICS = {b"\xde\x12\x04\x95", b"\x95\x04\x12\xde"}
MINIMUM_CANONICAL_MO_FILES = 708


class Validator:
    def __init__(self):
        self.assertions = 0

    def check(self, condition, message):
        self.assertions += 1
        if not condition:
            raise AssertionError(message)


def load_json(validator, path):
    validator.check(path.is_file(), f"missing JSON file: {path}")
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    validator.check(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def validate_json(validator, share):
    json_dir = share / "iso-codes" / "json"
    data_counts = {}
    for domain in DOMAINS:
        suffix = domain.removeprefix("iso_")
        data = load_json(validator, json_dir / f"{domain}.json")
        key = DATA_KEYS[domain]
        validator.check(
            key in data and isinstance(data[key], list) and data[key],
            f"missing non-empty {key!r} records in {domain}.json",
        )
        data_counts[domain] = len(data[key])
        schema = load_json(validator, json_dir / f"schema-{suffix}.json")
        validator.check(
            isinstance(schema.get("properties"), dict) and schema["properties"],
            f"missing schema properties in schema-{suffix}.json",
        )
    return data_counts


def validate_xml(validator, share, data_counts):
    xml_dir = share / "xml" / "iso-codes"
    for domain in DOMAINS:
        path = xml_dir / f"{domain}.xml"
        validator.check(path.is_file(), f"missing XML file: {path}")
        root = element_tree.parse(path).getroot()
        validator.check(root.tag == XML_ROOTS[domain], f"unexpected XML root: {path}")
        records = root.findall(f".//{XML_ENTRY_TAGS[domain]}")
        validator.check(
            len(records) == data_counts[domain],
            f"XML record count drift for {domain}: {len(records)} != {data_counts[domain]}",
        )
        if domain == "iso_3166-1":
            withdrawn = root.findall(".//iso_3166_3_entry")
            validator.check(
                len(withdrawn) == data_counts["iso_3166-3"],
                "ISO 3166-1 compatibility XML lost withdrawn-country records",
            )

    for alias, target in XML_ALIASES.items():
        path = xml_dir / alias
        validator.check(path.is_symlink(), f"compatibility path is not a symlink: {path}")
        validator.check(os.readlink(path) == target, f"unexpected symlink target: {path}")


def validate_pkg_config(validator, share):
    path = share / "pkgconfig" / "iso-codes.pc"
    validator.check(path.is_file(), f"missing pkg-config file: {path}")
    fields = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key] = value
        elif "=" in line:
            key, value = line.split("=", 1)
            fields[key] = value
    validator.check(fields.get("Version") == "4.20.1", "incorrect pkg-config version")
    validator.check(
        fields.get("domains", "").split() == list(DOMAINS),
        "pkg-config domain inventory drift",
    )


def validate_translations(validator, share):
    locale_dir = share / "locale"
    validator.check(locale_dir.is_dir(), f"missing locale directory: {locale_dir}")
    canonical = []
    for domain in DOMAINS:
        matches = sorted(locale_dir.glob(f"*/LC_MESSAGES/{domain}.mo"))
        validator.check(matches, f"no translations installed for {domain}")
        canonical.extend(matches)
    validator.check(
        len(canonical) >= MINIMUM_CANONICAL_MO_FILES,
        f"only {len(canonical)} canonical .mo files were installed",
    )
    for path in canonical:
        validator.check(path.stat().st_size > 4, f"empty translation file: {path}")
        with path.open("rb") as handle:
            validator.check(handle.read(4) in MO_MAGICS, f"invalid MO magic: {path}")


def main(argv):
    if len(argv) != 2:
        print("usage: test_verify.py PACKAGE_ROOT", file=sys.stderr)
        return 2
    package_root = pathlib.Path(argv[1])
    validator = Validator()
    validator.check(package_root.is_dir(), f"missing package root: {package_root}")
    share = package_root / "share"
    data_counts = validate_json(validator, share)
    validate_xml(validator, share, data_counts)
    validate_pkg_config(validator, share)
    validate_translations(validator, share)
    print(f"ISO_CODES_VALIDATION_PASS assertions={validator.assertions}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except (AssertionError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ISO_CODES_VALIDATION_FAIL: {error}", file=sys.stderr)
        sys.exit(1)
