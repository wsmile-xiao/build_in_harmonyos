#!/usr/bin/env python3
"""Deterministic validation for the packaged wireless regulatory database."""

import argparse
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile


EXPECTED_TEXT_SHA256 = (
    "c137c85ab9d60d78fa5045fba0d3e2588a50adc12c5119db9d32ed3751773dc2"
)
EXPECTED_DATABASE_SHA256 = (
    "2fb33ca0074db573e05ef7dd50bb45b63c0ff98b7e852e1105ebad536fae8e6b"
)
EXPECTED_SIGNATURE_SHA256 = (
    "c941c08f51c93e46722293b85631604c3740d86c3de0c75f79aef50d2e919179"
)


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


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_database(tools_dir, database_text):
    sys.path.insert(0, str(tools_dir))
    try:
        from dbparse import DBParser
        from dbparse import SyntaxError as DatabaseSyntaxError
    finally:
        sys.path.pop(0)

    with database_text.open(encoding="utf-8") as source:
        return (
            DBParser(warn=lambda _message: None).parse(source),
            DBParser,
            DatabaseSyntaxError,
        )


def binary_country_codes(database_path):
    data = database_path.read_bytes()
    if len(data) < 12:
        raise ValidationError("compiled database is truncated")
    magic, version = struct.unpack_from(">II", data, 0)
    codes = []
    offset = 8
    while data[offset : offset + 4] != b"\0\0\0\0":
        if offset + 4 > len(data):
            raise ValidationError("compiled country table is unterminated")
        codes.append(data[offset : offset + 2])
        offset += 4
    return magic, version, codes


def malformed_database_is_rejected(parser_class, syntax_error, temp_dir):
    malformed = Path(temp_dir) / "malformed-db.txt"
    malformed.write_text(
        "country US:\n\t(100 - 50 @ 20), (20)\n",
        encoding="utf-8",
    )
    try:
        with malformed.open(encoding="utf-8") as source:
            parser_class(warn=lambda _message: None).parse(source)
    except syntax_error:
        return True
    return False


def validate(root):
    assertions = Assertions()
    data_dir = root / "share" / "wireless-regdb"
    tools_dir = data_dir / "tools"
    docs_dir = root / "share" / "doc" / "wireless-regdb"
    database_text = data_dir / "db.txt"
    database_binary = data_dir / "regulatory.db"
    database_signature = data_dir / "regulatory.db.p7s"
    compiler = tools_dir / "db2fw.py"
    parser = tools_dir / "dbparse.py"
    readme = docs_dir / "README"
    license_file = root / "licenses" / "LICENSE"

    required = (
        database_text,
        database_binary,
        database_signature,
        compiler,
        parser,
        readme,
        license_file,
    )
    assertions.check(
        all(path.is_file() for path in required),
        "all packaged data, tools, documentation, and license files exist",
    )
    assertions.check(
        sha256(database_text) == EXPECTED_TEXT_SHA256,
        "db.txt matches the authoritative release payload",
    )
    assertions.check(
        sha256(database_binary) == EXPECTED_DATABASE_SHA256,
        "regulatory.db matches the authoritative release payload",
    )
    assertions.check(
        sha256(database_signature) == EXPECTED_SIGNATURE_SHA256,
        "regulatory.db.p7s matches the authoritative release signature",
    )

    license_text = license_file.read_text(encoding="utf-8")
    assertions.check(
        "Permission to use, copy, modify, and/or distribute" in license_text
        and "THE SOFTWARE IS PROVIDED \"AS IS\"" in license_text,
        "the complete ISC license grant and disclaimer are packaged",
    )
    readme_text = readme.read_text(encoding="utf-8")
    assertions.check(
        "wireless-regdb" in readme_text
        and "dbparse.py" in readme_text
        and "db2fw.py" in readme_text,
        "the packaged README documents the database parser and compiler",
    )

    countries, parser_class, syntax_error = parse_database(
        tools_dir,
        database_text,
    )
    permissions = [
        rule
        for country in countries.values()
        for rule in country.permissions
    ]
    unique_rules = set(permissions)
    unique_wmm_rules = {
        rule.wmmrule for rule in unique_rules if rule.wmmrule is not None
    }
    assertions.check(len(countries) == 182, "all 182 country records parse")
    assertions.check(
        all(
            len(code) == 2 and (code.isalpha() or code == b"00")
            for code in countries
        ),
        "all domains use alpha2 codes or the global 00 identifier",
    )
    assertions.check(
        {b"US", b"CN", b"DE", b"JP"} <= set(countries),
        "representative FCC, ETSI, and JP domains are present",
    )
    assertions.check(
        (
            countries[b"US"].dfs_region,
            countries[b"CN"].dfs_region,
            countries[b"DE"].dfs_region,
            countries[b"JP"].dfs_region,
        )
        == (1, 1, 2, 3),
        "representative DFS regions match FCC, ETSI, and JP assignments",
    )
    assertions.check(
        tuple(len(countries[code].permissions) for code in (b"US", b"CN", b"DE", b"JP"))
        == (11, 7, 7, 8),
        "representative country rule counts match the release",
    )
    assertions.check(
        len(permissions) == 1013,
        "the database contains 1013 country permission assignments",
    )
    assertions.check(
        len(unique_rules) == 244,
        "the database contains 244 unique regulatory rules",
    )
    assertions.check(
        len(unique_wmm_rules) == 1,
        "the shared WMM rule set parses deterministically",
    )

    with tempfile.TemporaryDirectory(prefix="wireless-regdb-test-") as temp_dir:
        regenerated = Path(temp_dir) / "regulatory.db"
        result = subprocess.run(
            [sys.executable, str(compiler), str(regenerated), str(database_text)],
            cwd=tools_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        assertions.check(
            result.returncode == 0
            and regenerated.read_bytes() == database_binary.read_bytes(),
            "packaged db2fw.py regenerates regulatory.db byte for byte",
        )

        magic, version, codes = binary_country_codes(database_binary)
        assertions.check(
            magic == 0x52474442 and version == 20,
            "compiled database header has the expected magic and format version",
        )
        assertions.check(
            codes == sorted(countries),
            "compiled country table exactly matches the text database",
        )
        assertions.check(
            malformed_database_is_rejected(
                parser_class,
                syntax_error,
                temp_dir,
            ),
            "an inverted frequency range is rejected",
        )

    if assertions.count != 18:
        raise ValidationError(
            f"expected 18 assertions, executed {assertions.count}"
        )
    print("wireless-regdb: 18/18 semantic assertions passed")


def main():
    parser = argparse.ArgumentParser()
    roots = parser.add_mutually_exclusive_group(required=True)
    roots.add_argument("--source-root", type=Path)
    roots.add_argument("--package-root", type=Path)
    arguments = parser.parse_args()

    if arguments.source_root:
        with tempfile.TemporaryDirectory(
            prefix="wireless-regdb-source-layout-"
        ) as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "share" / "wireless-regdb"
            tools_dir = data_dir / "tools"
            docs_dir = root / "share" / "doc" / "wireless-regdb"
            license_dir = root / "licenses"
            tools_dir.mkdir(parents=True)
            docs_dir.mkdir(parents=True)
            license_dir.mkdir(parents=True)
            source = arguments.source_root
            for filename in (
                "db.txt",
                "regulatory.db",
                "regulatory.db.p7s",
            ):
                shutil.copy2(source / filename, data_dir / filename)
            for filename in ("dbparse.py", "db2fw.py"):
                shutil.copy2(source / filename, tools_dir / filename)
            shutil.copy2(source / "README", docs_dir / "README")
            shutil.copy2(source / "LICENSE", license_dir / "LICENSE")
            validate(root)
    else:
        validate(arguments.package_root)


if __name__ == "__main__":
    main()
