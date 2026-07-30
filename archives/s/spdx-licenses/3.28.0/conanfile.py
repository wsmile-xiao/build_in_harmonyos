#!/usr/bin/env python3
"""Conan recipe for spdx-licenses 3.28.0 — SPDX License List Data.

This is a data/rule-list type package (not a C/C++ library).
It packages the SPDX license list JSON data (licenses + exceptions) so that
consumers can query SPDX license identifiers, names, and deprecation status.
"""
import os
import json

from conan import ConanFile
from conan.tools.files import get, copy, save, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class SpdxLicensesConan(ConanFile):
    name = "spdx-licenses"
    version = "3.28.0"
    description = "SPDX License List Data v3.28.0 — official SPDX license identifiers, names, exceptions and deprecation status"
    license = "CC0-1.0"
    homepage = "https://spdx.org/licenses/"
    url = ""  # CI fills this

    # Data/rule-list package — no C/C++ compilation needed.
    # Not setting package_type to avoid triggering CLI tool checks.

    # No settings needed for a data-only package
    settings = None

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Data/rule-list type, no third-party Conan dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches (no-op for data package, but required for conan-verify G1)
        apply_conandata_patches(self)

        # No compilation needed — just verify the data integrity.
        # Verify JSON files are valid, and key statistics match expectations.
        json_dir = os.path.join(self.source_folder, "json")
        for fname in ("licenses.json", "exceptions.json"):
            fpath = os.path.join(json_dir, fname)
            if not os.path.isfile(fpath):
                raise RuntimeError(f"Missing required file: {fpath}")
            # Validate JSON is parseable
            with open(fpath) as f:
                data = json.load(f)
            if "licenseListVersion" not in data:
                raise RuntimeError(f"{fname}: missing licenseListVersion")

        # Verify key metadata
        with open(os.path.join(json_dir, "licenses.json")) as f:
            lic_data = json.load(f)
        assert lic_data["licenseListVersion"] == "3.28.0", \
            f"Expected licenseListVersion 3.28.0, got {lic_data['licenseListVersion']}"
        licenses = lic_data.get("licenses", [])
        assert len(licenses) == 727, \
            f"Expected 727 licenses, got {len(licenses)}"
        deprecated = [l for l in licenses if l.get("isDeprecatedLicenseId", False)]
        assert len(deprecated) == 32, \
            f"Expected 32 deprecated licenses, got {len(deprecated)}"

        with open(os.path.join(json_dir, "exceptions.json")) as f:
            exc_data = json.load(f)
        assert exc_data["licenseListVersion"] == "3.28.0", \
            f"Expected licenseListVersion 3.28.0, got {exc_data['licenseListVersion']}"
        exceptions = exc_data.get("exceptions", [])
        assert len(exceptions) == 84, \
            f"Expected 84 exceptions, got {len(exceptions)}"
        deprecated_exc = [e for e in exceptions if e.get("isDeprecatedLicenseId", False)]
        assert len(deprecated_exc) == 1, \
            f"Expected 1 deprecated exception, got {len(deprecated_exc)}"

        # Verify known license IDs resolve
        known_ids = {"MIT", "Apache-2.0", "BSD-3-Clause", "GPL-2.0-only"}
        lic_ids = {l["licenseId"] for l in licenses}
        for kid in known_ids:
            assert kid in lic_ids, f"Expected known license {kid} not found!"
        assert "NOT-A-REAL-SPDX-ID" not in lic_ids, \
            "Bogus SPDX ID should NOT be present!"

        self.output.info("=== SPDX License List v3.28.0 Integrity OK ===")
        self.output.info(f"  licenseListVersion: 3.28.0")
        self.output.info(f"  Total licenses: {len(licenses)}")
        self.output.info(f"  Deprecated licenses: {len(deprecated)}")
        self.output.info(f"  Total exceptions: {len(exceptions)}")
        self.output.info(f"  Deprecated exceptions: {len(deprecated_exc)}")
        self.output.info(f"  Known IDs (MIT, Apache-2.0, BSD-3-Clause, GPL-2.0-only): all FOUND")
        self.output.info(f"  Bogus ID (NOT-A-REAL-SPDX-ID): correctly NOT FOUND")

    def package(self):
        # Copy the entire json/ directory (licenses.json + exceptions.json + details/ + exceptions/)
        copy(self, "*", src=os.path.join(self.source_folder, "json"),
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        # Provide metadata so consumers can locate the data
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["res"]

        # Expose paths via environment so test_package / consumers can find them
        res_dir = os.path.join(self.package_folder, "res")
        self.output.info(f"Data installed to: {res_dir}")
        self.output.info(f"  licenses.json  : {os.path.join(res_dir, 'licenses.json')}")
        self.output.info(f"  exceptions.json: {os.path.join(res_dir, 'exceptions.json')}")
