#!/usr/bin/env python3
"""Conan recipe for visit_struct 1.2.0.

visit_struct is a miniature header-only C++11 library for struct-field
reflection: VISITABLE_STRUCT registers fields, and visit_struct::for_each
/ field_count / get_name visit them without macros at the call site.
Header-only: package() installs the headers under include/visit_struct/.

Upstream drives its tests through Boost.Build (b2/Jamroot.jam). The
CI-less-dependency subset that needs no Boost is three runtime test
programs, which build() compiles and executes when run_upstream_tests
is on:
  - test_visit_struct.cpp        (C++11, assert-based runtime checks)
  - test_visit_struct_intrusive.cpp (C++11, intrusive syntax variant)
  - test_fully_visitable.cpp     (C++14, compile-time visitability)
The two Boost-dependent tests (boost_fusion / boost_hana) are part of
the upstream suite but require Boost headers; they are declared in the
PR body and not built here, matching upstream's own "Could not find
boost, skipping boost tests" fallback in Jamroot.jam.

OHOS notes: upstream's GNU_FLAGS include -Werror; we compile without
-Werror (clang 15 warning policy differs) but the unmodified upstream
test sources are compiled and executed, and a failing assert aborts
the test binary, so the suite is genuine.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class VisitStructConan(ConanFile):
    name = "visit_struct"
    version = "1.2.0"
    description = "visit_struct - miniature header-only C++11 library for struct-field reflection"
    license = "BSL-1.0"
    homepage = "https://github.com/cbeck88/visit_struct"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/v/visit_struct/1.2.0"
    topics = ("reflection", "header-only", "visitation", "cpp11")
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
            self.output.info("Cross-building: upstream tests skipped at build time")
            return

        # R33: compiler must come from Conan conf, never bare shell env vars.
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = exes.get("cpp") or "clang++"

        sf = self.source_folder
        bf = self.build_folder
        # (source, C++ standard) — matches Jamroot.jam targets; the boost
        # fusion/hana tests are excluded (upstream skips them without Boost).
        tests = (
            ("test_visit_struct.cpp", "c++11"),
            ("test_visit_struct_intrusive.cpp", "c++11"),
            ("test_fully_visitable.cpp", "c++14"),
        )
        for src, std in tests:
            name = os.path.splitext(src)[0]
            out = os.path.join(bf, name)
            self.run(
                f'"{cxx}" -std={std} -O1 -I"{os.path.join(sf, "include")}" '
                f'"{os.path.join(sf, src)}" -o "{out}"',
                env="conanbuild")
        self.output.info(f"visit_struct upstream tests: {len(tests)}/{len(tests)} built OK")

        passed = 0
        for src, _std in tests:
            name = os.path.splitext(src)[0]
            self.run(f'"{os.path.join(bf, name)}"', env="conanbuild")
            passed += 1
            self.output.info(f"visit_struct upstream test {name}: exit 0 (PASS)")
        self.output.info(f"visit_struct upstream tests executed: {passed}/{len(tests)} passed")

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include", "visit_struct"),
             dst=os.path.join(self.package_folder, "include", "visit_struct"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_target_name", "visit_struct::visit_struct")
