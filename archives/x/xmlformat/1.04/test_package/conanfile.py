#!/usr/bin/env python3
"""Conan test_package for xmlformat 1.04 — Conan L1 official test.

Runs the smoke test script test_xmlformat.sh, which feeds a tiny XML
document to the installed `xmlformat` binary and verifies it produces
properly indented output (R34: substantively calls the packaged API).

CI runs this automatically via `conan create` (which invokes test_package).
"""
from conan import ConanFile


class XmlformatTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /bin/sh (mksh) cannot execute ELF binaries; bash runs the
        # smoke script which in turn execs the installed xmlformat binary.
        import os
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_xmlformat.sh xmlformat", env="conanrun")
