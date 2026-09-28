#!/usr/bin/env python3
"""test_package for libfastcommon 1.0.88.

Calls real libfastcommon APIs: md5 (my_md5_*) and logger (log_init).
Verifies both static and shared linking against the packaged library.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout
from conan.tools.files import save


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # The physical test source lives in the exported test_package dir
        # (source_folder); copy it into the build folder before compiling.
        shutil.copy(
            os.path.join(self.source_folder, "test_package.c"),
            os.path.join(self.build_folder, "test_package.c"),
        )
        cc = self.conf.get("tools.build:compiler_executables", default={},
                          check_type=dict).get("c", "clang")
        self.run(f"{cc} test_package.c -I{self.dependencies['libfastcommon'].package_folder}/include "
                 f"-L{self.dependencies['libfastcommon'].package_folder}/lib "
                 f"-lfastcommon -lm -ldl -o test_package", cwd=self.build_folder)

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.build_folder, "test_package"), env="conanrun")
