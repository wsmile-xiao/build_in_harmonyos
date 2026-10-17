#!/usr/bin/env python3
"""Conan test_package for cute_files 1.0.0 — exercises the real public API.

Builds test_cute_files.c with the system C compiler against the packaged
cute_files.h, then runs the binary. The test defines CUTE_FILES_IMPLEMENTATION
and exercises cf_dir_open / cf_read_file / cf_dir_next / cf_dir_close to
traverse a real directory, cf_file_exists and cf_match_ext / cf_get_ext,
asserting each result. Emits HMBS_TEST_PACKAGE_RESULT.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout


class CuteFilesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Compile the test TU with CUTE_FILES_IMPLEMENTATION using the same
        # compiler from the active profile (clang on OHOS). Include dir comes
        # straight from the packaged dependency.
        dep = self.dependencies["cute_files"]
        include = os.path.join(dep.package_folder, "include")
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_cute_files.c")
        exe = os.path.join(self.build_folder, "test_cute_files")
        self.run(f"{cc} -std=c99 -O2 -I{include} -o {exe} {src}",
                 cwd=self.build_folder)

    def test(self):
        if cross_building(self):
            self.output.info("Cross-compiling: test binary built but not run on host")
            return
        exe = os.path.join(self.build_folder, "test_cute_files")
        self.run(exe)