#!/usr/bin/env python3
"""Conan recipe — libmill 1.18 (Go-style concurrency in C).

libmill is Martin Sustrik's port of Go's concurrency primitives to C:
coroutines (``go``), channels (``chmake``/``chs``/``chr``) and a ``choose``
statement, on top of a coroutine scheduler that keeps a coroutine's stack in a
heap-allocated block and switches with ``sigsetjmp``/``siglongjmp`` on targets
other than x86-64.

Build system : CMake.  The project ships a CMakeLists.txt and an autotools
               setup; the GitHub tarball has no generated ``configure``, so
               CMake is the usable path here.
Package form : a library (``libmill.a`` by default, ``libmill.so`` with
               ``-o shared=True``) plus the single public header ``libmill.h``.

OHOS handling — two upstream details are dealt with from the recipe, plus one
small test patch:

  * ``cmake_minimum_required(VERSION 2.8.7)`` — CMake >= 3.28 refuses
    compatibility below 3.5, so ``CMAKE_POLICY_VERSION_MINIMUM=3.5`` is passed
    through the toolchain (the same trick other recipes in this repository use
    for old CMakeLists).
  * upstream declares **no** ``install()`` rules at all, so ``package()``
    copies the header and the library directly.  ``millinclude_HEADERS =
    libmill.h`` in the autotools Makefile.am is the authority for which header
    is public; libmill.h is self-contained (it includes no internal headers).
  * ``patches/0001`` moves tests/file.c's test file out of the hard-coded
    ``/tmp/file1``: HarmonyOS mounts /tmp read-only, mfopen() returned NULL
    there and the NULL dereference crashed the case with SIGSEGV (Release
    builds define NDEBUG, so the test's own ``assert(f1)`` was compiled out).

Upstream tests: 18 CTest cases, one per file in tests/ — executed for real in
build().  One of them cannot run on HarmonyOS and is reported as NOT_RUN rather
than as a pass (see UPSTREAM_EXCLUDED_TESTS and test_package/MANIFEST.yml).
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibmillConan(ConanFile):
    name = "libmill"
    version = "1.18"
    description = "libmill — Go-style concurrency in C (coroutines, channels, choose)"
    license = "MIT"
    homepage = "http://libmill.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    # CMakeLists.txt globs tests/*.c and registers one add_test() per file.
    UPSTREAM_TEST_CASES = 18

    # HarmonyOS returns EPERM for bind() on an AF_UNIX socket (verified on the
    # device: "PermissionError [Errno 1] Operation not permitted"), so upstream's
    # tests/unix.c cannot run there.  The test file itself is NOT modified --
    # the case is simply not executed, and it is reported as NOT_RUN with that
    # reason rather than counted as a pass.
    UPSTREAM_EXCLUDED_TESTS = ("test_unix",)

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libmill is prepared for Linux/OHOS targets only")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # cmake_minimum_required(VERSION 2.8.7): CMake >= 3.28 refuses
        # compatibility below 3.5 unless the policy floor is stated.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the full CTest suite and report what actually happened.

        CMakeLists.txt globs tests/*.c, so every test file becomes one
        executable and one registered CTest case.  ctest's own summary line is
        parsed rather than trusted from a declaration, and a non-zero exit is a
        build failure.
        """
        log = os.path.join(self.build_folder, "upstream-tests.log")
        exclude = "|".join(self.UPSTREAM_EXCLUDED_TESTS)
        self.run(
            'ctest --output-on-failure --timeout 120 -E "{exclude}" '
            '> "{log}" 2>&1; echo "EXIT=$?" >> "{log}"'.format(exclude=exclude, log=log),
            cwd=self.build_folder)

        with open(log, "r", errors="replace") as handle:
            text = handle.read()

        exit_code = None
        for line in text.splitlines():
            if line.startswith("EXIT="):
                exit_code = line[5:].strip()

        passed = failed = None
        match = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", text)
        if match:
            failed = int(match.group(2))
            total = int(match.group(3))
            passed = total - failed

        executed = self.UPSTREAM_TEST_CASES - len(self.UPSTREAM_EXCLUDED_TESTS)
        self.output.info(
            "libmill upstream tests: {}/{} executed passed, {} failed "
            "(ctest exit {}); NOT_RUN: {}".format(
                passed, executed, failed, exit_code,
                ", ".join(self.UPSTREAM_EXCLUDED_TESTS)))

        if exit_code != "0" or (failed is not None and failed != 0):
            raise ConanException(
                "libmill upstream tests failed: ctest exit={} failed={} (of {}); "
                "full log: {}".format(exit_code, failed, self.UPSTREAM_TEST_CASES, log))

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "libmill.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "libmill.so*", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        else:
            copy(self, "libmill.a", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["mill"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libmill")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
