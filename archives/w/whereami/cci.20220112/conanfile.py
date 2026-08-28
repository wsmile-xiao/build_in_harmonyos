#!/usr/bin/env python3
"""Conan recipe for whereami cci.20220112 using CMake."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class WhereamiConan(ConanFile):
    name = "whereami"
    version = "cci.20220112"
    description = "Locate the current executable and module on the file system"
    license = ("MIT", "WTFPL-2.0")
    homepage = "https://github.com/gpakosz/whereami"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    no_copy_source = True
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("whereami is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["WHEREAMI_OHOS"] = self.settings.os == "OHOS"
        tc.generate()

    def _build_environment(self):
        environment = Environment()
        if self.settings.os == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            compiler = compilers.get("c") or "clang"
            llvm_lib = os.path.join(
                os.path.dirname(os.path.dirname(os.path.realpath(compiler))), "lib"
            )
            if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
                environment.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return environment

    def build(self):
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure(build_script_folder=self.export_sources_folder)
            cmake.build()

    def package(self):
        copy(self, "LICENSE.*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["whereami"]
        if self.settings.os == "OHOS":
            self.cpp_info.system_libs = ["dl"]
