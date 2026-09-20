#!/usr/bin/env python3
"""Conan recipe for sheenbidi 3.0.0 - Unicode Bidirectional Algorithm.

SheenBidi is a lightweight, fast implementation of the Unicode Bidirectional
Algorithm (UBA): it resolves embedding levels and visual runs for paragraphs
and lines of bidirectional text.  It only needs the standard C library.

OHOS notes
----------
* Plain CMake C project (``CMakeLists.txt``), no dependencies and no non-x86
  intrinsics, so it builds with the OHOS clang unchanged.
* The upstream test suite is a custom STANDALONE_TESTING framework: 16 test
  executables (``SB_CONFIG_UNITY=OFF`` required), each run with the
  ``Tools/Unicode`` data directory as argument.  The executables always exit 0,
  so failures are detected through CMake's ``FAIL_REGULAR_EXPRESSION``; the
  suite is run through ``ctest`` (with a raised per-test timeout to tolerate the
  shared device).
* ``test_package`` reproduces the upstream/Debian smoke test (mixed
  Arabic/Latin text + mirroring) with explicit assertions.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=2.0"


class SheenBidiConan(ConanFile):
    name = "sheenbidi"
    version = "3.0.0"
    description = ("Lightweight implementation of the Unicode Bidirectional "
                   "Algorithm (UBA) for paragraphs, lines and runs")
    license = "Apache-2.0"
    homepage = "https://github.com/Tehreer/SheenBidi"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sheenbidi OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Tests are only built in non-unity mode (see CMakeLists.txt).
        toolchain.variables["SB_CONFIG_UNITY"] = False
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        log = os.path.join(self.build_folder, "upstream-ctest.log")
        # The test executables link the shared libSheenBidi.so from the build
        # tree; add the build folder to the loader path.
        self.run('LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" '
                 'ctest --output-on-failure --timeout 600 > "{}" 2>&1'.format(
                     self.build_folder, log),
                 cwd=self.build_folder)
        with open(log, "r", errors="replace") as handle:
            content = handle.read()
        match = re.search(
            r"(\d+)% tests passed(?:, (\d+) tests failed)? out of (\d+)", content)
        if not match:
            raise ConanException("could not read the ctest summary from the log")
        failed = int(match.group(2) or 0)
        total = int(match.group(3))
        if failed:
            raise ConanException("{} of {} upstream tests failed".format(failed, total))
        self.output.info("upstream ctest suite: {}/{} tests passed".format(total, total))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["SheenBidi"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "SheenBidi")
        self.cpp_info.set_property("cmake_target_name", "SheenBidi::SheenBidi")
        self.cpp_info.set_property("pkg_config_name", "sheenbidi")
