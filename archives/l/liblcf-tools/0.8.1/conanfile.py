#!/usr/bin/env python3
"""Conan recipe for the liblcf 0.8.1 command-line tools.

The upstream CMake project builds liblcf together with lcfstrings and lcf2xml.
This package exposes the two installed executables and statically links the
internal liblcf target, so it remains an application package rather than a
second copy of the liblcf development library.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class LiblcfToolsConan(ConanFile):
    name = "liblcf-tools"
    version = "0.8.1"
    description = "Command-line tools for converting and extracting RPG Maker LCF data"
    license = "MIT"
    homepage = "https://github.com/EasyRPG/liblcf"
    url = "https://github.com/EasyRPG/liblcf"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lcf2xml needs the upstream XML reader; the upstream unit suite also
        # exercises the INI reader, so keep that optional component enabled.
        self.requires("expat/2.8.2.1")
        self.requires("inih/r58")
        self.requires("icu4c/77")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                f"liblcf-tools is validated for OpenHarmony PC only, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["LIBLCF_WITH_INI"] = True
        tc.variables["LIBLCF_WITH_ICU"] = True
        tc.variables["LIBLCF_WITH_XML"] = True
        tc.variables["LIBLCF_UPDATE_MIMEDB"] = False
        tc.variables["LIBLCF_ENABLE_TOOLS"] = True
        tc.variables["LIBLCF_ENABLE_TESTS"] = True
        tc.variables["LIBLCF_ENABLE_BENCHMARKS"] = False
        tc.variables["LIBLCF_ENABLE_INSTALL"] = True
        tc.variables["CMAKE_INSTALL_BINDIR"] = "bin"
        # CMake 4.x rejects projects whose maximum policy version is older
        # unless the compatibility floor is explicitly selected.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.16"
        tc.cache_variables["ICU_ROOT"] = self.dependencies["icu4c"].package_folder
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # `tools` is the upstream custom target for lcfstrings/lcf2xml.
        cmake.build(target="tools")
        # The upstream project has a custom `check` target rather than ctest;
        # it builds and runs the doctest-based test_runner. Apply the Conan run
        # environment because Expat is a shared dependency on OHOS.
        with VirtualRunEnv(self).vars().apply():
            cmake.build(target="check")

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # The executables statically contain liblcf. Do not ship the internal
        # static library or development headers in this separate tools package.
        for directory in ("include", "lib", "share", "lib64"):
            rmdir(self, os.path.join(self.package_folder, directory))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
