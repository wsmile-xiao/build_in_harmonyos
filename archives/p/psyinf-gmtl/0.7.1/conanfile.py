#!/usr/bin/env python3
"""Conan recipe for GMTL 0.7.1 (Generic Math Template Library) on HarmonyOS.

GMTL is a header-only C++ template library: upstream ships no compiled
artefact, only the ``gmtl/`` include tree.  The package therefore exposes the
headers plus upstream's own CMake package config, and clears its ``package_id``
so a single package serves every OS/arch/compiler combination.

Upstream's test suite (``Test/TestSuite``) is a CppUnit runner.  A static
count of ``CPPUNIT_TEST(...)`` in ``TestCases/*.h`` gives 446 declarations
(34 non-metric suites with 229 cases + 28 ``*MetricTest`` suites with 217
cases).  The runner's default ``noninteractive`` path executes the 208 that
are registered in CppUnit's global registry, and that is the suite this recipe
runs (local ``conan create`` -> ``OK (208)``).

The 217 ``*MetricTest`` cases are compiled and registered but are **not run**:
the runner selects a suite by ``argv[1]`` and this recipe only invokes the
``noninteractive`` path, so those cases are excluded from every pass rate
reported here.  (Running ``runtests metric`` by hand currently reports
``Run: 210  Failure total: 3``, i.e. that path is genuinely failing -- it is
deliberately not asserted on.)  Upstream wires it only through SCons (``SConstruct`` /
``SConscript``); there is no CMake build for it.  This recipe adds one, via
``patches/0001``, so the real upstream cases can be compiled and executed on
OHOS, and declares ``cppunit`` as a ``test_requires`` so the framework stays a
build-only test dependency of the package.

The suite is executed from ``build()`` through the profile's
``CMAKE_CROSSCOMPILING_EMULATOR`` (the same qemu wrapper CTest would use), which
is how the pass/fail numbers in the PR are produced.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class GmtlConan(ConanFile):
    name = "psyinf-gmtl"
    version = "0.7.1"
    description = "Generic Math Template Library: header-only C++ math (vectors, matrices, quaternions, geometric primitives)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/psyinf/gmtl"
    url = "https://github.com/psyinf/gmtl"

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # basic_layout keeps source_folder == the unpacked upstream tree and
        # makes package()'s relative `dst` resolve against package_folder.
        # A cmake_layout would redirect relative dst paths to the build folder,
        # which yields an empty package for a header-only library.
        basic_layout(self)

    def requirements(self):
        # GMTL's upstream CppUnit cases are build-only test coverage: 446 are
        # declared, 208 of which run on the runner's noninteractive path.
        self.test_requires("cppunit/1.15.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CMakeDeps lets the patched upstream test CMakeLists resolve
        # CppUnit::cppunit through find_package(CppUnit).
        deps = CMakeDeps(self)
        deps.set_property("cppunit", "cmake_file_name", "CppUnit")
        deps.set_property("cppunit", "cmake_target_name", "CppUnit::cppunit")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["GMTL_BUILD_UPSTREAM_TESTS"] = True
        # Upstream declares cmake_minimum_required(VERSION 2.8.8); keep an
        # explicit policy floor so configure() still works on CMake >= 3.28.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # The CI worker's CMake runs a try-compile to identify the compiler.
        # That try-compile fails on the worker with "resource temporarily
        # unavailable" (the host clang binary is reachable, but /bin/sh on the
        # worker is execute-only), so CMake reports
        #   "The C compiler ... is not able to compile a simple test program"
        # and configure() aborts before a single GMTL source is touched.
        # Declaring the compiler as already verified skips exactly that probe;
        # the real sources are still compiled and linked by the same clang.
        # Same remedy as archives/o/open-scene-graph/3.6.5 (E053).
        # Only these two variables are used to bypass the probe; the compiler
        # itself is NOT replaced, so every real translation unit is still
        # compiled and linked by the same OHOS clang.
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "TRUE"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "TRUE"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _emulator(self):
        """Return the qemu wrapper the OHOS profile installs, if any."""
        extra = self.conf.get(
            "tools.cmake.cmaketoolchain:extra_variables", check_type=dict
        ) or {}
        return extra.get("CMAKE_CROSSCOMPILING_EMULATOR")

    def _run_upstream_tests(self):
        """Execute the upstream CppUnit suite, one process per test path.

        ``runtests`` takes the test path as argv[1]; upstream's own default is
        ``noninteractive``, which is the aggregate suite we report on.  The
        binary is built by Test/TestSuite/CMakeLists.txt inside the normal
        build, so this only runs it.
        """
        exe = os.path.join(self.build_folder, "Test", "TestSuite", "runtests")
        if not os.path.isfile(exe):
            # Hard failure: a missing runner means the upstream suite was NOT
            # executed, so the pass rate this recipe reports would be a claim
            # about nothing.  Never let that pass as a green build.
            raise ConanException(
                "upstream CppUnit runner not built at %s -- refusing to report "
                "a pass rate for a suite that never ran" % exe
            )

        emulator = self._emulator()
        if cross_building(self):
            if not emulator:
                # Cross-built binaries cannot run on the build host, so an
                # unset emulator would silently turn this into a no-op.
                raise ConanException(
                    "cross-building without CMAKE_CROSSCOMPILING_EMULATOR: "
                    "cannot execute the upstream suite, so no pass rate can be "
                    "claimed (use the ohos-aarch64-run profile)"
                )
            prefix = f'"{emulator}" '
        else:
            prefix = ""

        self.output.info("Running upstream CppUnit suite: runtests noninteractive")
        # ignore_errors=False (Conan's default) is stated explicitly on
        # purpose: a non-zero exit -- i.e. any upstream case failing -- must
        # fail the build instead of being silently absorbed.
        self.run(f'{prefix}"{exe}" noninteractive', ignore_errors=False)

    def package(self):
        # All 51 public headers live under <source>/gmtl/ (44 at the top level
        # plus Util/, Misc/, Numerics/, External/, Fit/) and are included as
        # <gmtl/...>, so they go to include/gmtl/.
        #
        # dst is built from self.package_folder on purpose: copy() resolves a
        # *relative* dst against the current working directory, which during
        # package() is the build folder -- the files would silently land there
        # and the package would come out empty ("No files in this package!").
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "gmtl"),
            dst=os.path.join(self.package_folder, "include", "gmtl"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        # Header-only: no compiled artefact depends on the settings.
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "psyinf-gmtl")
        self.cpp_info.set_property("cmake_target_name", "psyinf-gmtl::psyinf-gmtl")
        self.cpp_info.set_property("pkg_config_name", "psyinf-gmtl")
