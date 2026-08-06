"""Conan recipe for Aften 0.0.8."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AftenConan(ConanFile):
    name = "aften"
    version = "0.0.8"
    description = "A/52 (AC-3) audio encoder"
    license = "LGPL-2.0-or-later"
    homepage = "https://aften.sourceforge.net/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SHARED"] = bool(self.options.shared)
        tc.variables["BINDINGS_CXX"] = False
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        variables = {}
        if str(self.settings.os) == "OHOS":
            variables["OHOS_ARCH"] = (
                "x86_64" if str(self.settings.arch) == "x86_64" else "arm64-v8a"
            )
        cmake.configure(variables=variables)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["aften"]
        if str(self.settings.os) != "Windows":
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "aften")
        self.cpp_info.set_property("cmake_target_name", "aften::aften")
        self.cpp_info.bindirs = ["bin"]
