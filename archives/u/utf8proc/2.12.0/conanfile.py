#!/usr/bin/env python3
"""Conan recipe for upstream utf8proc 2.12.0 on OpenHarmony PC."""
import glob
from pathlib import Path
import re

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Utf8ProcConan(ConanFile):
    name = "utf8proc"
    version = "2.12.0"
    description = "Clean C library for processing UTF-8 Unicode data"
    license = "MIT"
    homepage = "https://github.com/JuliaStrings/utf8proc"
    url = "https://github.com/JuliaStrings/utf8proc"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Upstream defaults this to OFF. Native builds run the real suite;
        # cross builds must never execute target binaries on Windows.
        tc.variables["UTF8PROC_ENABLE_TESTING"] = can_run(self)
        tc.generate()

        # The OHOS SDK linker needs its bundled libxml2 at runtime on CI.
        env = Environment()
        for sdk_lib in glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
        ):
            env.append("LD_LIBRARY_PATH", sdk_lib)
        env.vars(self).save_script("utf8proc_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if can_run(self):
            # CTest succeeds even with zero registered tests.
            registration = Path(self.build_folder) / "CTestTestfile.cmake"
            if not registration.is_file():
                raise RuntimeError("utf8proc CTest registration is missing")
            count = len(re.findall(r"(?m)^add_test\(", registration.read_text()))
            if count < 9:
                raise RuntimeError(f"utf8proc registered only {count} tests")
            self.output.info(f"utf8proc registered {count} upstream tests")
            test_env = Environment()
            test_env.append("LD_LIBRARY_PATH", self.build_folder)
            with test_env.vars(self).apply():
                self.run("ctest --output-on-failure", cwd=self.build_folder)
        else:
            self.output.info("Cross build: upstream target tests require native OHOS execution")

    def package(self):
        CMake(self).install()
        # LICENSE.md includes both the MIT and the Unicode data notices.
        copy(self, "LICENSE.md", self.source_folder, self.package_folder + "/licenses")

    def package_info(self):
        self.cpp_info.libs = ["utf8proc"]
