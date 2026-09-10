#!/usr/bin/env python3
"""Conan recipe for KCP 2.1.1.

KCP is a small C library whose upstream CMake project also builds a C++
network simulator test.  The recipe keeps that test enabled for native
HarmonyOS builds and packages the installed library and public header.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


required_conan_version = ">=2.0"


class KcpConan(ConanFile):
    name = "kcp"
    version = "2.1.1"
    package_type = "library"

    description = "A Fast and Reliable ARQ Protocol"
    homepage = "https://github.com/skywind3000/kcp"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = True
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe(
            "fPIC", True
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if can_run(self):
            test_binary = os.path.join(self.build_folder, "kcp_test")
            self.run(f'"{test_binary}"', env="conanbuild")
        else:
            self.output.info(
                "Cross build: kcp_test was built but not executed in this environment."
            )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["kcp"]
        self.cpp_info.set_property("cmake_file_name", "kcp")
        self.cpp_info.set_property("cmake_target_name", "kcp::kcp")
        self.cpp_info.set_property("pkg_config_name", "kcp")
