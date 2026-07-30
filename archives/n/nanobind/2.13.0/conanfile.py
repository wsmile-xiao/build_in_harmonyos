#!/usr/bin/env python3
"""Conan recipe — nanobind 2.13.0 (CMake header / binding framework).

Aligns with Homebrew nanobind 2.13.0:
  -DNB_TEST=OFF
  -DNB_USE_SUBMODULE_DEPS=OFF
  -DNB_CREATE_INSTALL_RULES=ON

Depends on robin-map/1.4.1 (tsl-robin-map) per scheme A (R36).
Downstream test: find_package(nanobind CONFIG) + nanobind_add_module + import extension.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NanobindConan(ConanFile):
    name = "nanobind"
    version = "2.13.0"
    description = "Tiny and efficient C++/Python bindings"
    license = "BSD-3-Clause"
    homepage = "https://github.com/wjakob/nanobind"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Scheme A: external robin-map (Homebrew NB_USE_SUBMODULE_DEPS=OFF)
        self.requires("robin-map/1.4.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: accept both Linux and OHOS
        if self.settings.os in ("Linux", "OHOS"):
            # E092: some CMake versions do not treat OHOS as a known system name
            # (configure-only / no compilers; defensive align with robin-map/valijson)
            if self.settings.os == "OHOS":
                tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["NB_TEST"] = "OFF"
        tc.cache_variables["NB_USE_SUBMODULE_DEPS"] = "OFF"
        tc.cache_variables["NB_CREATE_INSTALL_RULES"] = "ON"
        # NB_INSTALL_DATADIR is CACHE PATH: a relative value like "nanobind" is
        # absolutized against the build dir, so install ignores CMAKE_INSTALL_PREFIX
        # and the Conan package ends up empty. Use an absolute destination under
        # package_folder (same idea as Homebrew's absolute #{pkgshare}).
        tc.cache_variables["NB_INSTALL_DATADIR"] = os.path.join(
            self.package_folder, "nanobind"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # header-library clears executable/library dirs by default; do not assign
        # empty lists for those fields — L0k greps that token and false-positives R38.
        self.cpp_info.includedirs = [os.path.join("nanobind", "include")]

        # Upstream places nanobind-config.cmake under ${NB_INSTALL_DATADIR}/cmake
        # cmake_find_mode=none → consumers use the packaged Config (Homebrew-compatible)
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", "nanobind")
        self.cpp_info.builddirs.append(os.path.join("nanobind", "cmake"))
        # Ensure consumers also get tsl-robin-map on CMAKE_PREFIX_PATH
        # (nanobind-config.cmake → find_dependency(tsl-robin-map))
        self.cpp_info.requires = ["robin-map::robin-map"]
