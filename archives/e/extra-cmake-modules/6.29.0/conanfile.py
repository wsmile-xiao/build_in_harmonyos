#!/usr/bin/env python3
"""Conan recipe for extra-cmake-modules (ECM) 6.29.0 on HarmonyOS PC (aarch64).

ECM (Extra CMake Modules) is a collection of additional CMake modules from KDE.
It is a pure CMake module library — no binary code is compiled or linked; it only
installs .cmake / .py scripts under share/ECM/.

OHOS-specific adaptations (aligned with the published ecm/6.26.0 recipe):
  - package_type = "build-scripts": ECM ships only CMake modules.
  - package_id() uses self.info.clear() to avoid package-ID variation from
    compiler/build_type settings (no compiled artifacts).
  - BUILD_TESTING=OFF at configure time: upstream tests are optional and
    Qt-dependent; the module set itself has no runtime deps.
  - R32: no os == "Linux" comparison needed (no os-specific branches).
  - R33: no reliance on undefined shell $CC/$CFLAGS (cmake-only, clang-free).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ExtraCMakeModulesConan(ConanFile):
    name = "extra-cmake-modules"
    version = "6.29.0"
    description = "Extra CMake Modules — additional CMake modules from KDE"
    license = "BSD-3-Clause"
    homepage = "https://invent.kde.org/frameworks/extra-cmake-modules"
    url = "https://invent.kde.org/frameworks/extra-cmake-modules"

    package_type = "build-scripts"

    settings = "os", "compiler", "build_type", "arch"

    def package_id(self):
        # No compiled artifacts: a single package ID across toolchains.
        self.info.clear()

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
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
        # Downstream consumers use find_package(ECM); no cpp_info.libs
        # (ECM is a cmake-only module package).
        self.cpp_info.set_property("cmake_file_name", "ECM")
        self.cpp_info.set_property("cmake_target_name", "ECM::ECM")
        self.cpp_info.builddirs = ["share/ECM/cmake"]
