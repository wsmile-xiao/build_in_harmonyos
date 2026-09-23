#!/usr/bin/env python3
"""Conan recipe — packcc 3.1.0 (CMake, single-file C).

packcc is a packrat parsing-expression-grammar (PEG) parser generator for C:
it reads a ``.peg`` grammar file and emits a self-contained ``parser.c`` /
``parser.h`` pair.  The whole implementation is a single translation unit
``src/packcc.c`` compiled into a command-line tool ``packcc``; no third-party
runtime dependencies beyond libc.

OHOS adaptation notes:
  - Upstream CMake is used as-is.  The conan CMakeToolchain drives the OHOS
    SDK clang so the produced ``packcc`` executable carries a valid code
    signature and keeps its exec bit on HMDFS (vala/platform_folders same
    toolchain path).
  - Debug builds add ASan/UBSan flags via the toolchain; CI uses the ohos
    Release profile so sanitizer libs are never required.
  - Upstream ``--target check`` needs the Bats-core shell harness plus
    Uncrustify, and it compiles *and executes* generated parsers on the build
    host — none of which is available in the OHOS build sandbox.  Real
    end-to-end verification therefore happens in test_package (R34), which runs
    the installed ``packcc`` on a bundled grammar and asserts the generated
    parser sources (see test_package/MANIFEST.yml).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class PackccConan(ConanFile):
    name = "packcc"
    version = "3.1.0"
    description = "packcc — PEG (Parsing Expression Grammar) parser generator for C"
    license = "MIT"
    homepage = "https://github.com/arithy/packcc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def validate(self):
        # R32: settings.os 判断必须覆盖 "Linux" 和 "OHOS"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "packcc recipe currently supports Linux and OHOS builds only"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()  # bin/packcc + share/packcc/import (upstream CMake install)
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # 让消费方 test 运行期能把 packcc 放到 PATH（tool_requires 场景同效）
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
