#!/usr/bin/env python3
"""Conan recipe for waf — a Python-based build system.

Waf is distributed as a single Python script (not a tarball).
This recipe downloads the script, installs it to bin/, and verifies
it runs correctly via test_package.
"""
import os

from conan import ConanFile
from conan.tools.files import download, copy, apply_conandata_patches, export_conandata_patches


class WafConan(ConanFile):
    name = "waf"
    version = "2.1.9"
    description = "Python-based build system designed for cross-platform software projects"
    license = "BSD-3-Clause"
    homepage = "https://waf.io/"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # waf is a pure Python script — no compiler/build_type dependency
        del self.info.settings.compiler
        del self.info.settings.build_type

    def source(self):
        # waf is a single Python script (not an archive) — download without extraction
        # get() would try to extract it as a zip (waf contains an embedded zip)
        src = self.conan_data["sources"]
        download(self, src["url"], "waf", sha256=src["sha256"])

    def build(self):
        # Waf is a single Python script — no compilation needed
        apply_conandata_patches(self)

    def package(self):
        copy(self, "waf", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        # Ensure the script is executable
        waf_path = os.path.join(self.package_folder, "bin", "waf")
        if os.path.exists(waf_path):
            os.chmod(waf_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
