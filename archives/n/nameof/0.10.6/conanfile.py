#!/usr/bin/env python3
"""Conan recipe for nameof 0.10.6.

nameof is a header-only C++17 library that obtains the name of a variable,
type, function, macro, or enum as a string at compile time (NAMEOF /
NAMEOF_TYPE / NAMEOF_ENUM, nameof::nameof_type<> ...).

Header-only: package() installs the single header ``include/nameof.hpp``.
To satisfy the "上游完整测试真实执行" gate, build() compiles and runs the two
upstream doctest suites (``test/test.cpp`` and ``test/test_aliases.cpp``,
95 TEST_CASE + 49 SUBCASE) against the *vendored* doctest header
(``test/3rdparty/doctest``) — no network and no external dependency needed.

OHOS notes:
- The upstream ``test/CMakeLists.txt`` forces ``-Wall -Wextra
  -pedantic-errors -Werror`` which OHOS clang turns into hard errors, so we
  compile the suites directly here with warnings demoted (still the genuine
  upstream sources, unmodified).
- ``fmt`` is optional in the suite: ``test.cpp`` guards its fmt SUBCASE with
  ``__has_include(<fmt/format.h>)`` — it compiles and passes without fmt.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NameofConan(ConanFile):
    name = "nameof"
    version = "0.10.6"
    description = "nameof - header-only C++17 library to obtain names of variables, types, functions, macros, and enums"
    license = "MIT"
    homepage = "https://github.com/neargye/nameof"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/n/nameof/0.10.6"
    topics = ("reflection", "nameof", "header-only", "cpp17")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # header-only: package content is identical for every configuration
        self.info.clear()

    def validate(self):
        # R32: use `in`, never `==`
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"{self.name} is validated for Linux/OHOS/Windows/Macos/FreeBSD, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not self.options.run_upstream_tests:
            return
        if not can_run(self):
            self.output.info("Cross-building: upstream doctest suites skipped at build time")
            return

        # R33: compiler must come from Conan conf, never bare shell env vars.
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = exes.get("cpp") or "clang++"

        sf = self.source_folder
        inc = os.path.join(sf, "include")
        tp = os.path.join(sf, "test", "3rdparty")
        flags = "-std=c++17 -O2"

        suites = (
            ("test.cpp", "nameof_test"),
            ("test_aliases.cpp", "nameof_aliases_test"),
        )
        for src, out in suites:
            self.output.info(f"Compiling upstream doctest suite {src}")
            self.run(
                f'"{cxx}" {flags} -I"{inc}" -I"{tp}" '
                f'"{os.path.join(sf, "test", src)}" -o "{os.path.join(self.build_folder, out)}"',
                env="conanbuild",
            )
        for _, out in suites:
            self.output.info(f"Running upstream doctest suite {out}")
            self.run(f'"{os.path.join(self.build_folder, out)}"', env="conanbuild")

    def package(self):
        copy(self, "nameof.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_target_name", "nameof::nameof")
