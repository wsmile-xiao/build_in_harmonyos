#!/usr/bin/env python3
"""Conan recipe for ninja 1.13.2 — a small build system with a focus on speed.

Ninja is a command-line tool (executable), not a library. Build system: CMake.
OHOS adaptation notes (see notes.md / reports/upstream-test-ledger.md):
  1. ppoll() on the OHOS PC kernel returns ENOMEM at runtime (measured), so the
     upstream NINJA_FORCE_PSELECT option is forced ON to use pselect() instead.
  2. BUILD_TESTING=ON with GTest provided via test_requires(gtest/1.17.0) from
     the ohpcd registry — avoids FetchContent download of googletest from GitHub.
  3. Upstream never wired src/status_test.cc into any test target (omitted from
     both CMakeLists.txt and configure.py); a minimal patch includes it so the
     two StatusTest cases are built and run (source-test-entry recovery).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class NinjaConan(ConanFile):
    name = "ninja"
    version = "1.13.2"
    description = "Small build system with a focus on speed"
    license = "Apache-2.0"
    homepage = "https://ninja-build.org/"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # GTest for the upstream test suite; registry has OHOS armv8 packages.
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Enable the upstream test suite (GTest comes from conan, no GitHub fetch).
        tc.variables["BUILD_TESTING"] = "ON"
        # ninja's CMakeLists calls find_package(GTest) (capital G). CMakeDeps
        # generates lowercase config, so point GTest_DIR at the conan gtest
        # package's own CMake config (GTestConfig.cmake with GTest::gtest).
        gtest = self.dependencies.get("gtest")
        if gtest and gtest.package_folder:
            cfg = os.path.join(gtest.package_folder, "lib", "cmake", "GTest")
            if os.path.isdir(cfg):
                tc.variables["GTest_DIR"] = cfg
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # OHOS adaptation, passed as configure variables so they override the
        # upstream `option()` defaults in CMakeLists.txt:
        #  - NINJA_FORCE_PSELECT=ON: ppoll() fails at runtime with ENOMEM on
        #    this platform (toybox/bionic poll limitation) -> use pselect().
        #  - NINJA_SUBPROCESS_SHELL=/data/service/hnp/bin/bash: /bin/sh on this
        #    platform lacks POSIX signal semantics (child killed by SIGHUP
        #    exits WIFEXITED(129) instead of WIFSIGNALED); bash behaves POSIX.
        cmake.configure(variables={
            "NINJA_FORCE_PSELECT": "ON",
            "NINJA_SUBPROCESS_SHELL": "/data/service/hnp/bin/bash",
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
