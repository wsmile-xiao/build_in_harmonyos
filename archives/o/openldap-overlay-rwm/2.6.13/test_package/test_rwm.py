#!/usr/bin/env python3
"""Validate the packaged rwm module and load it through slapd."""

import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("usage: test_rwm.py SLAPD RWM_MODULE CONFIG")

    slapd, module, config = sys.argv[1:]
    for label, path in (("slapd", slapd), ("rwm module", module), ("config", config)):
        if not os.path.isfile(path):
            raise RuntimeError(f"{label} was not found: {path}")

    with open(config, encoding="utf-8") as handle:
        config_text = handle.read()

    expected = (
        "include ",
        f'modulepath "{os.path.dirname(module)}"',
        f"moduleload {os.path.basename(module)}",
        "overlay rwm",
        'rwm-suffixmassage "dc=virtual,dc=example" "dc=example,dc=com"',
    )
    for directive in expected:
        if directive not in config_text:
            raise RuntimeError(f"generated config is missing: {directive}")

    schema_line = next(
        line for line in config_text.splitlines() if line.startswith("include ")
    )
    core_schema = schema_line.removeprefix("include ").strip('"')
    if not os.path.isfile(core_schema):
        raise RuntimeError(f"configured OpenLDAP core schema was not found: {core_schema}")

    subprocess.run([slapd, "-Tt", "-f", config], check=True)
    print("openldap-overlay-rwm: module load and configuration check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
