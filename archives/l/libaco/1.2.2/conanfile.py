#!/usr/bin/env python3
"""Conan recipe for libaco 1.2.2 (HarmonyOS / aarch64 port).

Upstream (hnes/libaco) ships only aco.c / aco.h / acosw.S plus ad-hoc
make.sh/test.sh that compile test programs — there is no configure or
CMake. The HarmonyOS port adds:
  * patches/0001-aarch64-support.patch — aarch64 context-switch assembly
    (acosw.S), aco.h/aco.c aarch64 register layout, and an extra aarch64
    OHOS test program (test_aco_ohos_aarch64.c).
  * patches/0002-add-cmakelists.patch — a minimal CMakeLists.txt that
    builds the installable library from the same upstream sources.

Default build is static (R26-style; not a system library, but static is
the safe default for a coroutine runtime).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibacoConan(ConanFile):
    name = "libaco"
    version = "1.2.2"
    description = "libaco: C coroutine library (aarch64/HarmonyOS port)"
    license = "Apache-2.0"
    homepage = "https://github.com/hnes/libaco"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            exe = os.path.join(self.build_folder, "test_aco_tutorial_0")
            if os.path.isfile(exe):
                self.run(f'"{exe}"', env="conanrun")

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["aco"]
        self.cpp_info.set_property("cmake_file_name", "libaco")
        self.cpp_info.set_property("cmake_target_name", "libaco::libaco")
