#!/usr/bin/env python3
"""Conan recipe for BCUnit 5.3.113 on HarmonyOS (OHOS).

BCUnit is a C unit testing framework forked from CUnit by Belledonne
Communications (Linphone stack; consumed by bctoolbox's tester).  5.3.113 is
the linphone-sdk 5.3 line snapshot of the repository: it still declares
project(BCUnit VERSION "3.0.2") internally but carries the APIs the 5.3 line
needs (CU_Suite.pUserData, CU_automated_enable_partial_junit).  Upstream
primary build system is CMake with no third-party dependencies.

OHOS-specific handling (evidence in notes.md):
- The internal test target bcunit_test lost its framework include directories
  in the 5.3.113 CMake refactor, so the upstream self-test could not be built
  (patches/0001-fix-bcunit-test-include-directories.patch)
- CU_trace_handler storage moved from Basic/Basic.c into framework Util.c so
  the upstream self-test program links again
  (patches/0002-move-cu-trace-handler-to-framework.patch)

The upstream self-test (ENABLE_BCUNIT_TEST=ON) is built and executed inside
build() so the assertion counts are recorded in the package build log.
"""

import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)

required_conan_version = ">=2.0"

# Upstream internal self-test counters for this pinned source revision
# (BCUnit/Sources/Test/test_bcunit.c, which itself always returns 0).  build()
# asserts them so an assertion regression fails the package build.
UPSTREAM_TEST_ASSERTIONS = 3915


class BcunitConan(ConanFile):
    name = "bcunit"
    version = "5.3.113"
    description = (
        "C unit testing framework forked from CUnit by Belledonne "
        "Communications (static/shared library with basic, automated and "
        "console interfaces)"
    )
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/BelledonneCommunications/bcunit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("unit-testing", "testing", "framework", "c")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # bcunit is self-contained: no third-party dependencies
        # (upstream configure probes only optional Curses, disabled here).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream 5.3.113 builds a single `bcunit` target with add_library()
        # and no library-type switch of its own, so the Conan toolchain's
        # BUILD_SHARED_LIBS (derived from the shared option) drives it.
        # Keep the package to the library itself: the internal self-test is
        # built for the upstream-test run below, examples/doxygen/curses stay
        # disabled (upstream defaults except the latter two which are OFF too).
        tc.variables["ENABLE_BCUNIT_TEST"] = "ON"
        tc.variables["ENABLE_BCUNIT_EXAMPLES"] = "OFF"
        tc.variables["ENABLE_BCUNIT_DOC"] = "OFF"
        tc.variables["ENABLE_BCUNIT_CURSES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run the upstream self-test for real; its assertion counters are the
        # upstream test evidence recorded in this build log.  The program is
        # not installed (only the bcunit library is), so the package contents
        # are unaffected.  Upstream's test_bcunit.c main() returns 0
        # unconditionally, so the exit code alone cannot gate a regression:
        # capture the output and assert the counters the archive claims.
        tester = os.path.join(
            self.build_folder, "BCUnit", "Sources", "Test", "test_bcunit"
        )
        if not os.path.isfile(tester):
            raise ConanException(f"upstream self-test was not built at {tester}")
        test_log = os.path.join(self.build_folder, "upstream-self-test.log")
        # tee keeps the run visible in the build log while storing a copy to
        # assert on below.
        self.run(f'"{tester}" 2>&1 | tee "{test_log}"', env="conanbuild")
        text = load(self, test_log)
        assertions = re.search(r"Total Number of Assertions:\s*(\d+)", text)
        failures = re.search(r"Failures:\s*(\d+)", text)
        if assertions is None or failures is None:
            raise ConanException(
                f"upstream self-test produced no result counters, see {test_log}"
            )
        self.output.info(
            f"upstream self-test: {assertions.group(1)} assertions, "
            f"{failures.group(1)} failures"
        )
        if (int(assertions.group(1)) != UPSTREAM_TEST_ASSERTIONS) or (
            int(failures.group(1)) != 0
        ):
            raise ConanException(
                f"upstream self-test regression: {assertions.group(1)} assertions, "
                f"{failures.group(1)} failures "
                f"(expected {UPSTREAM_TEST_ASSERTIONS}/0), see {test_log}"
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream configures bcunit.pc with *relative* dirs (empty prefix,
        # exec_prefix=bin, libdir=lib, -Llib / -Iinclude) because
        # CMakeLists.txt assigns CMAKE_INSTALL_BINDIR/LIBDIR directly.
        # Anchor every path at the package folder so the file is usable as
        # installed.  Ordered replacements: the bare prefix line first, the
        # longer exec_prefix line before any substring collisions.  Each
        # source pattern is asserted present first: upstream .pc template
        # changes must fail the build instead of silently shipping a .pc with
        # relative paths.
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "bcunit.pc")
        pc = load(self, pc_path)
        for old, new in (
            ("prefix=\n", f"prefix={self.package_folder}\n"),
            ("exec_prefix=bin\n", "exec_prefix=${prefix}/bin\n"),
            ("libdir=lib\n", "libdir=${prefix}/lib\n"),
            ("includedir=include\n", "includedir=${prefix}/include\n"),
            ("Libs: -Llib -lbcunit\n", "Libs: -L${prefix}/lib -lbcunit\n"),
            ("Cflags: -Iinclude\n", "Cflags: -I${prefix}/include\n"),
        ):
            if old not in pc:
                raise ConanException(
                    f"bcunit.pc: expected upstream pattern {old.strip()!r} not found; "
                    "the .pc template changed, review the path anchoring"
                )
            pc = pc.replace(old, new, 1)
        save(self, pc_path, pc)

    def package_info(self):
        # Products match upstream install(): headers under include/BCUnit
        # (consumed as #include "BCUnit/BCUnit.h"), lib/libbcunit.so or
        # lib/libbcunit.a depending on the shared option; no executables are
        # installed.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["bcunit"]
        self.cpp_info.set_property("pkg_config_name", "bcunit")
