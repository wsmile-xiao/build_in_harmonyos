#!/usr/bin/env python3
"""Conan recipe for j4-dmenu 3.2 (j4-dmenu-desktop) — C++17 + CMake.

Upstream produces a single executable, `bin/j4-dmenu-desktop`, and by default
fetches spdlog / fmt / Catch2 from GitHub at configure time (FetchContent).
For a pinned, offline-capable build the recipe configures with NO_DOWNLOAD=ON,
which makes upstream's CMakeLists.txt fall back to find_package() and pick up
the Conan-provided packages instead.

Adapted for OpenHarmony PC (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class J4DmenuConan(ConanFile):
    name = "j4-dmenu"
    version = "3.2"
    description = "j4-dmenu-desktop — fast .desktop entry launcher for dmenu (C++17)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/enkore/j4-dmenu-desktop"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Upstream installs one executable and nothing else.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"with_tests": [True, False]}
    # Static dependencies: the shipped launcher must be self-contained, and
    # Catch2's catch_discover_tests executes the test binary at build time,
    # where the shared-library run environment (conanrun) is not active yet.
    # These must be graph-wide defaults: per-edge options lose to the value
    # spdlog propagates for fmt and raise an "options conflicts" warning.
    default_options = {
        "with_tests": True,
        "spdlog/*:shared": False,
        "fmt/*:shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("spdlog/1.17.0")
        self.requires("fmt/12.2.0")
        if self.options.with_tests:
            # Host-context test-only dependency: linked into upstream's
            # j4-dmenu-tests binary, never into the shipped executable.
            self.requires("catch2/3.16.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # spdlog ships its fmt shims under include/spdlog/fmt/*.h and the ohpcd
        # package lists include/spdlog on the include path. With that directory
        # present, `#include <fmt/ranges.h>` resolves to spdlog's own shim
        # instead of fmt's header; the shim's `#pragma once` then swallows the
        # include, so the real fmt/ranges.h is never parsed and fmt::join is
        # undeclared. Keep only `include` so <fmt/...> always reaches fmt.
        spdlog_cpp_info = self.dependencies["spdlog"].cpp_info
        spdlog_cpp_info.includedirs = [
            os.path.join(self.dependencies["spdlog"].package_folder, "include")
        ]

        tc = CMakeToolchain(self)
        # Build against the Conan-provided dependencies, not the FetchContent
        # git clones upstream defaults to (NO_DOWNLOAD also forces every
        # WITH_GIT_* switch off).
        tc.variables["NO_DOWNLOAD"] = "ON"
        tc.variables["WITH_TESTS"] = "ON" if self.options.with_tests else "OFF"
        # Feed the packaged version instead of upstream's `git describe`
        # fallback on version.txt, so a tarball build reports a stable version.
        tc.variables["OVERRIDE_VERSION"] = self.version
        if self.options.with_tests:
            # CMakeDeps' generated Catch2 config does not add the package's
            # CMake helper modules to CMAKE_MODULE_PATH, so upstream's
            # `include(Catch)` cannot locate Catch.cmake. Point it there.
            catch2_dir = os.path.join(
                self.dependencies["catch2"].package_folder, "lib", "cmake", "Catch2"
            )
            tc.variables["CMAKE_MODULE_PATH"] = catch2_dir.replace("\\", "/")
        tc.generate()

        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_tests and can_run(self):
            # Upstream CTest suite. The pytest system tests drive a live
            # dmenu/X session, so only the Catch2 unit tests run here.
            # ctest is invoked directly: CMake.test() forwards cli_args to the
            # build tool, not to ctest.
            self.run(
                f'ctest --test-dir "{self.build_folder}" '
                "--output-on-failure -j8 --timeout 60 -E pytest"
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
