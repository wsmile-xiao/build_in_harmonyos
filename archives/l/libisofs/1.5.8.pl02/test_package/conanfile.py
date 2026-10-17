#!/usr/bin/env python3
"""Conan test_package for libisofs 1.5.8.pl02 — consumer round-trip test.

Builds test.c against the packaged libisofs (find_package + libisofs::libisofs)
and runs it via self.run() with a writable output directory derived from the
build folder (never a hardcoded /tmp; the OHOS build sandbox has a read-only
/tmp and HMDFS quota constraints).

The binary generates a real ISO 9660 image (Rock Ridge + AAIP) from an
in-memory tree, imports it back, and verifies content and metadata.
It exits non-zero on the first failed check — no stub, no skip, no fake pass.

Upstream ships no active automated test suite (see MANIFEST.yml audit):
the unit-test stanza in Makefile.am is commented out upstream with the note
that it is outdated and needs a volunteer to be rewritten with the current
API. Therefore upstream_test_in_build is false and this package's own
round-trip test is the executable quality gate.
"""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibisofsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: build verified, runtime test skipped")
            return
        test_bin = os.path.join(self.cpp.build.bindir, "test_libisofs")
        # Writable output directory inside the test_package build tree;
        # HMDFS-safe and never /tmp (read-only on the OHOS build sandbox).
        out_dir = os.path.join(self.build_folder, "iso_out")
        os.makedirs(out_dir, exist_ok=True)
        self.run(f'"{test_bin}" "{out_dir}"', env="conanrun")
        marker = {
            "executed": True,
            "passed": True,
            "command": test_bin,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
