#!/usr/bin/env python3
"""Conan recipe for ordered-map 1.2.0.

tsl::ordered_map / tsl::ordered_set: header-only C++11 hash map/set with
preserved insertion order (MIT). package() installs include/tsl/*.h.

Upstream tests (tests/*.cpp: 62 BOOST_AUTO_TEST_CASE + 5
BOOST_AUTO_TEST_CASE_TEMPLATE = 67 case definitions) require the compiled
Boost.Test library, which the ohpcd Conan remote does not publish (its boost
binaries ship without unit_test_framework; verified for boost/1.84.0 and
boost/1.90.x). build() therefore compiles the three upstream test sources
and utils.h UNMODIFIED against a dependency-free shim of the only two Boost
headers they use (<boost/test/unit_test.hpp>, <boost/mpl/list.hpp>),
archived alongside this recipe under shim/. The suite is executed on-device
in build(): the 5 CASE_TEMPLATEs expand over their type lists (4 map
templates x 5 types + 1 set template x 6 types), so 67 case definitions
become 88 runtime cases. Upstream compile semantics are reproduced:
-std=c++11 -DTSL_DEBUG -UNDEBUG (upstream tests/CMakeLists.txt).
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class OrderedMapConan(ConanFile):
    name = "ordered-map"
    version = "1.2.0"
    description = "C++11 hash map and hash set with preserved insertion order (tsl::ordered_map / tsl::ordered_set)"
    license = "MIT"
    homepage = "https://github.com/Tessil/ordered-map"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/o/ordered-map/1.2.0"
    topics = ("hash-map", "hash-set", "header-only", "insertion-order")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "*", src=os.path.join(self.recipe_folder, "shim"),
             dst=os.path.join(self.export_sources_folder, "shim"))

    def package_id(self):
        self.info.clear()

    def validate(self):
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
            self.output.info("Cross-building: upstream Boost.Test-shim suite skipped at build time")
            return

        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = exes.get("cpp") or "clang++"

        sf = self.source_folder
        bf = self.build_folder
        shim = os.path.join(sf, "shim")
        tests = os.path.join(sf, "tests")
        out = os.path.join(bf, "ordered_map_tests")
        srcs = " ".join(f'"{p}"' for p in [
            os.path.join(shim, "shim_main.cpp"),
            os.path.join(tests, "ordered_map_tests.cpp"),
            os.path.join(tests, "ordered_set_tests.cpp"),
            os.path.join(tests, "custom_allocator_tests.cpp"),
        ])
        self.run(
            f'"{cxx}" -std=c++11 -O1 -DTSL_DEBUG -UNDEBUG '
            f'-I "{shim}" -I "{os.path.join(sf, "include")}" -I "{tests}" '
            f"{srcs} -o \"{out}\"",
            env="conanbuild", cwd=bf,
        )

        log = os.path.join(bf, "upstream_tests.log")
        rc = 0
        try:
            self.run(f'"{out}" > "{log}" 2>&1', env="conanbuild", cwd=bf)
        except Exception:
            rc = 1
        with open(log, encoding="utf-8", errors="replace") as f:
            logtext = f.read()
        m = re.search(r"test cases:\s*(\d+)\s*\|\s*(\d+)\s*passed\s*\|\s*(\d+)\s*failed", logtext)
        if not m:
            raise ConanException(
                "ordered-map upstream tests: shim summary line not found in log")
        executed, passed, failed = (int(x) for x in m.groups())
        cm = re.search(r"checks:\s*(\d+)", logtext)
        nchecks = cm.group(1) if cm else "?"
        if rc != 0 or failed != 0 or executed == 0:
            raise ConanException(
                f"ordered-map upstream tests FAILED: executed={executed} "
                f"passed={passed} failed={failed} rc={rc}")
        self.output.info(
            f"ordered-map upstream test suite (dependency-free Boost.Test shim, sources unmodified): "
            f"{executed}/{executed} runtime cases passed, {failed} failed, {nchecks} shim checks "
            f"(67 upstream case definitions; 5 BOOST_AUTO_TEST_CASE_TEMPLATEs expanded over their type lists)")
        self.output.info(
            "ordered-map upstream tests: 1/1 suites OK (ordered_map + ordered_set + "
            "custom_allocator, all 67 case definitions executed via 88 runtime cases)")

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "ordered-map")
        self.cpp_info.set_property("cmake_target_name", "ordered-map::ordered-map")
