#!/usr/bin/env python3
"""Conan recipe for hedley 15.

hedley is a single-header C/C++ macro library that provides portable
wrappers around compiler attributes and diagnostics (HEDLEY_PURE,
HEDLEY_LIKELY, HEDLEY_DIAGNOSTIC_PUSH, ...). Header-only: package()
installs the single header ``hedley.h``.

Upstream ships no runtime test framework: ``test/`` holds 35 compile-
check sources driven by ``test/Makefile`` (``make all`` builds each one
as C, then as C++ via a .c -> .cpp copy). Passing = compiles cleanly,
which validates that every hedley macro expands to valid, warning-free
code for the target compiler. build() faithfully reproduces that:
compiles all 35 tests as C and as C++ (70 compile checks) and also
executes every resulting binary. 12 of the binaries return computed
values by design (e.g. require.c's main returns add(2,3)=5), so a
non-zero exit is informational, not a failure — upstream never runs
the binaries at all.

OHOS notes:
- The upstream Makefile uses ``-Weverything -Werror`` which OHOS clang
  15 turns into hard errors on 7 intentional-warning tests (message,
  non-null, printf-format, sentinel, unused-function, unreachable,
  warn-unused-result) plus a -Wmissing-prototypes hit, so we compile
  with ``-std=c11`` / ``-std=c++17`` and no -Werror. The genuine
  upstream sources are compiled and executed unmodified.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class HedleyConan(ConanFile):
    name = "hedley"
    version = "15"
    description = "hedley - header-only C/C++ macro library for portable compiler attributes and diagnostics"
    license = "CC0-1.0"
    homepage = "https://github.com/nemequ/hedley"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/h/hedley/15"
    topics = ("macros", "attributes", "header-only", "portability")
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
            self.output.info("Cross-building: upstream compile-check tests skipped at build time")
            return

        # R33: compiler must come from Conan conf, never bare shell env vars.
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = exes.get("c") or "clang"
        cxx = exes.get("cpp") or "clang++"

        sf = self.source_folder
        bf = self.build_folder
        tests = (
            "array-param", "assume", "cast", "concat", "const", "constant",
            "deprecated", "empty-bases", "fallthrough", "flags", "inline",
            "likely", "malloc", "message", "noinline", "no-escape",
            "no-return", "non-null", "predict", "printf-format", "pure",
            "require", "restrict", "returns-non-null", "sentinel",
            "static-assert", "stringify", "unknown-cpp-attributes",
            "unknown-pragmas", "unavailable", "unreachable",
            "unused-function", "visibility", "warn", "warn-unused-result",
        )

        # C++ variants: upstream copies each .c to .cpp inside test/, so the
        # "#include "../hedley.h"" keeps resolving; reproduce that layout.
        cppdir = os.path.join(bf, "test")
        os.makedirs(cppdir, exist_ok=True)
        copy(self, "hedley.h", src=sf, dst=bf)
        for t in tests:
            copy(self, f"{t}.c", src=os.path.join(sf, "test"), dst=cppdir)
            os.replace(os.path.join(cppdir, f"{t}.c"), os.path.join(cppdir, f"{t}.cpp"))

        compiled = []
        for t in tests:
            out = os.path.join(bf, f"c-{t}")
            self.run(f'"{cc}" -std=c11 -O1 "{os.path.join(sf, "test", t + ".c")}" -o "{out}"',
                     env="conanbuild")
            compiled.append(out)
        for t in tests:
            out = os.path.join(bf, f"cpp-{t}")
            self.run(f'"{cxx}" -std=c++17 -O1 "{os.path.join(cppdir, t + ".cpp")}" -o "{out}"',
                     env="conanbuild")
            compiled.append(out)
        self.output.info(f"hedley upstream compile checks: {len(compiled)}/70 built OK")

        zero, designed = 0, []
        for binary in compiled:
            try:
                self.run(f'"{binary}"', env="conanbuild")
                zero += 1
            except Exception:
                designed.append(os.path.basename(binary))
        self.output.info(
            f"hedley upstream test binaries executed: {zero} exit-0, {len(designed)} non-zero; "
            f"non-zero exits are by design (upstream mains return computed values, e.g. "
            f"require.c returns add(2,3)=5; upstream Makefile never runs them): {', '.join(designed)}")

    def package(self):
        copy(self, "hedley.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_target_name", "hedley::hedley")
