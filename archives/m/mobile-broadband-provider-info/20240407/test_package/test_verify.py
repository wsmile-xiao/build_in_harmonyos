#!/usr/bin/env python3
"""Validate the installed mobile-broadband-provider-info 20240407 data contract.

Consumer-level checks against the Conan package tree:
1. co-located data files (database + DTD + generated APN database),
2. DTD element declarations,
3. database structure (694 providers / 154 countries),
4. xsltproc-generated apns-conf.xml schema,
5. pkg-config metadata with the pcfiledir-relative pkgdatadir contract,
6. consumer flow resolution of the database through pkgdatadir.
"""

import pathlib
import sys
import xml.etree.ElementTree as element_tree

EXPECTED_VERSION = "20240407"
EXPECTED_PROVIDERS = 694
EXPECTED_COUNTRIES = 154
MINIMUM_APNS = 1000
PKGDATA_REL = pathlib.Path("share") / "mobile-broadband-provider-info"
PC_REL = pathlib.Path("share") / "pkgconfig" / "mobile-broadband-provider-info.pc"


class Validator:
    def __init__(self):
        self.assertions = 0

    def check(self, condition, message):
        self.assertions += 1
        if not condition:
            raise AssertionError(message)


def parse_pc_fields(path):
    # pkg-config 混合格式：关键字段用 "Name: value"，变量用 "var=value"
    fields = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key.strip()] = value.strip()
        elif "=" in line:
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
    return fields


def main(argv):
    if len(argv) != 2:
        print("usage: test_verify.py PACKAGE_ROOT", file=sys.stderr)
        return 2
    package_root = pathlib.Path(argv[1])
    validator = Validator()
    validator.check(package_root.is_dir(), f"missing package root: {package_root}")

    pkgdata = package_root / PKGDATA_REL
    database = pkgdata / "serviceproviders.xml"
    dtd = pkgdata / "serviceproviders.2.dtd"
    apns = pkgdata / "apns-conf.xml"

    # 1. co-located data files
    validator.check(database.is_file(), f"missing database: {database}")
    validator.check(dtd.is_file(), f"missing DTD: {dtd}")
    validator.check(apns.is_file(), f"missing generated APN database: {apns}")

    # 2. DTD contract
    dtd_text = dtd.read_text(encoding="utf-8", errors="replace")
    validator.check(
        "<!ELEMENT serviceproviders (country*)>" in dtd_text,
        "DTD lacks serviceproviders element declaration",
    )
    validator.check(
        "<!ELEMENT provider (name+, gsm?, cdma?)>" in dtd_text,
        "DTD lacks provider element declaration",
    )

    # 3. database structure
    root = element_tree.parse(database).getroot()
    validator.check(root.tag == "serviceproviders", f"unexpected database root: {root.tag}")
    countries = root.findall("country")
    validator.check(
        len(countries) == EXPECTED_COUNTRIES,
        f"country count drift: {len(countries)} != {EXPECTED_COUNTRIES}",
    )
    providers = root.findall(".//provider")
    validator.check(
        len(providers) == EXPECTED_PROVIDERS,
        f"provider count drift: {len(providers)} != {EXPECTED_PROVIDERS}",
    )
    validator.check(len(root.findall(".//gsm")) > 0, "database contains no GSM providers")

    # 4. generated APN database (xsltproc custom_target output)
    apns_root = element_tree.parse(apns).getroot()
    validator.check(apns_root.tag == "apns", f"unexpected APN root: {apns_root.tag}")
    validator.check(
        apns_root.get("version") == "8",
        f"unexpected APN schema version: {apns_root.get('version')}",
    )
    apn_count = len(apns_root.findall(".//apn"))
    validator.check(apn_count >= MINIMUM_APNS, f"too few APN entries: {apn_count} < {MINIMUM_APNS}")

    # 5. pkg-config metadata + relocation contract
    pc_path = package_root / PC_REL
    validator.check(pc_path.is_file(), f"missing pkg-config file: {pc_path}")
    fields = parse_pc_fields(pc_path)
    validator.check(
        fields.get("Name") == "mobile-broadband-provider-info",
        f"unexpected pkg-config Name: {fields.get('Name')}",
    )
    validator.check(
        fields.get("Version") == EXPECTED_VERSION,
        f"unexpected pkg-config Version: {fields.get('Version')}",
    )
    pkgdatadir = fields.get("pkgdatadir", "")
    validator.check(
        pkgdatadir == "${pcfiledir}/../mobile-broadband-provider-info",
        f"pkgdatadir is not the pcfiledir-relative contract: {pkgdatadir}",
    )
    validator.check(
        fields.get("database") == "${pkgdatadir}/serviceproviders.xml",
        f"unexpected database variable: {fields.get('database')}",
    )

    # 6. consumer flow: resolve the database through pkgdatadir
    resolved = pc_path.parent / ".." / "mobile-broadband-provider-info" / "serviceproviders.xml"
    validator.check(resolved.is_file(), f"pkgdatadir resolution broken: {resolved}")

    print(f"MBPI_VALIDATION_PASS assertions={validator.assertions}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except (AssertionError, OSError, element_tree.ParseError) as error:
        print(f"MBPI_VALIDATION_FAIL: {error}", file=sys.stderr)
        sys.exit(1)
