#!/usr/bin/env python3
"""Conan recipe for tng 1.8.2 — GROMACS TNG trajectory I/O library.

Build system: CMake (project TNG_IO, C).
TNG ships an optional internal zlib under external/zlib; upstream CMake
falls back to it automatically when system zlib is not found, so the
recipe needs no external requires.
OHOS notes:
- CMake 4.x dropped compatibility with cmake_minimum_required < 3.5;
  CMAKE_POLICY_VERSION_MINIMUM=3.5 is passed via the toolchain.
- Library package (libtng_io) only: tests/examples are not installed
  (R38: library type, no commands.json).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TngConan(ConanFile):
    name = "tng"
    version = "1.8.2"
    description = "GROMACS TNG trajectory file I/O library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/gromacs/tng"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x removed compatibility with cmake_minimum_required < 3.5
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["TNG_BUILD_FORTRAN"] = "OFF"
        tc.variables["TNG_BUILD_DOCUMENTATION"] = "OFF"
        # 内置 zlib（external/zlib）编译进 libtng_io，静态包自包含，避免
        # 外部 ZLIB::ZLIB PRIVATE 链接依赖不向消费者传递导致的未定义符号
        tc.variables["TNG_BUILD_OWN_ZLIB"] = "ON"
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
        self.cpp_info.libs = ["tng_io"]
        self.cpp_info.set_property("cmake_file_name", "tng_io")
        self.cpp_info.set_property("cmake_target_name", "tng_io::tng_io")
