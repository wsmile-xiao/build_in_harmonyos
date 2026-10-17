#!/usr/bin/env python3
"""Consumer test for asyncfuture: consumer smoke test + upstream full suite.

Runs two test layers:
1. test_asyncfuture — consumer assertions over the public API.
2. asyncfutureunittests — the upstream Qt Test suite copied verbatim from
   the source tarball (tests/), built against qtbase + qtdeclarative.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import get

# Upstream source (same URL/sha256 as the recipe's conandata.yml)
_UPSTREAM_URL = ("https://github.com/vpicaver/asyncfuture/archive/"
                 "refs/tags/v1.1.0.tar.gz")
_UPSTREAM_SHA256 = ("63c95c9ae14b91c14b3c89ac3fe5d6b32e8290b851ecbde92e"
                    "33120dfdded430")


class AsyncfutureTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Upstream suite needs Qt6 Qml/Quick/QuickTest (review clancyxie):
        # these modules live in qtdeclarative, not qtbase.
        self.requires("qtdeclarative/6.11.1", transitive_headers=True,
                      transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # asyncfuture ships its own asyncfutureConfig.cmake (header-only,
        # no CMakeDeps: qtbase/qtdeclarative set cmake_find_mode=none so
        # CMakeDeps can never emit usable Qt targets for the link interface).
        # Point CMake at the asyncfuture package root and the Qt packages'
        # bundled Qt6*Config.cmake dirs (adwaita-qt test_package pattern).
        af_prefix = self.dependencies["asyncfuture"].package_folder
        qt_prefix = self.dependencies["qtbase"].package_folder
        qml_prefix = self.dependencies["qtdeclarative"].package_folder
        tc = CMakeToolchain(self)
        # Qt6Config lives in the qtbase package; Qt6QmlConfig/Qt6QuickConfig
        # live in the qtdeclarative package. Qt only searches the additional
        # prefixes listed in QT_ADDITIONAL_PACKAGES_PREFIX_PATH for module
        # configs (qtdeclarative test_package pattern).
        tc.cache_variables["CMAKE_PREFIX_PATH"] = (
            f"{af_prefix};{qt_prefix}/lib/cmake")
        tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = qml_prefix
        tc.generate()
        # LD_LIBRARY_PATH for Qt6 shared libs at run time
        VirtualRunEnv(self).generate()
        # Copy the upstream test tree verbatim (R51: run upstream tests
        # unmodified) into the build folder. Dependency objects don't
        # expose source_folder, so fetch the same tarball via the
        # conan download cache.
        src_root = os.path.join(self.build_folder, "upstream_src")
        get(self, _UPSTREAM_URL, destination=src_root,
            sha256=_UPSTREAM_SHA256, strip_root=True)
        dst_tests = os.path.join(self.build_folder, "upstream_tests")
        if os.path.isdir(dst_tests):
            shutil.rmtree(dst_tests)
        shutil.copytree(os.path.join(src_root, "tests"), dst_tests)
        tc2_cache = dst_tests.replace("\\", "/")
        # Re-emit toolchain so the cache var lands in the same preset run
        # (CMakeLists reads UPSTREAM_TESTS_DIR at configure time).
        tc.cache_variables["UPSTREAM_TESTS_DIR"] = tc2_cache
        # Upstream tests include <asyncfuture.h> via the tarball root
        # (their CMakeLists adds ${CMAKE_SOURCE_DIR}); expose that root
        # since the suite is now built from a copied subdirectory.
        tc.cache_variables["UPSTREAM_SRC_DIR"] = src_root.replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        bindir = self.cpp.build.bindir
        # Layer 1: consumer smoke test
        self.run(os.path.join(bindir, "test_asyncfuture"), env="conanrun")
        # Layer 2: upstream full suite (no display server on device); the
        # target lives in its add_subdirectory build dir, not bindir
        upstream_bin = os.path.join(self.build_folder, "upstream_tests_build",
                                    "asyncfutureunittests")
        self.run(f"QT_QPA_PLATFORM=offscreen {upstream_bin}", env="conanrun")
