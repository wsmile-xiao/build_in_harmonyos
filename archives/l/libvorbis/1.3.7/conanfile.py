#!/usr/bin/env python3
"""Conan recipe for libvorbis 1.3.7."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, replace_in_file


class LibvorbisConan(ConanFile):
    name = "libvorbis"
    version = "1.3.7"
    description = "Reference implementation of the Vorbis audio codec"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/vorbis/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires(
            "libogg/1.3.6",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(
            self,
            "CMakeLists.txt",
            "cmake_minimum_required(VERSION 2.8.12)",
            "cmake_minimum_required(VERSION 3.5)",
        )

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["INSTALL_CMAKE_PACKAGE_MODULE"] = True
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Vorbis")

        vorbis = self.cpp_info.components["vorbis"]
        vorbis.libs = ["vorbis"]
        vorbis.set_property("cmake_target_name", "Vorbis::vorbis")
        vorbis.set_property("pkg_config_name", "vorbis")
        vorbis.requires = ["libogg::libogg"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            vorbis.system_libs = ["m"]

        enc = self.cpp_info.components["vorbisenc"]
        enc.libs = ["vorbisenc"]
        enc.set_property("cmake_target_name", "Vorbis::vorbisenc")
        enc.set_property("pkg_config_name", "vorbisenc")
        enc.requires = ["vorbis"]

        file = self.cpp_info.components["vorbisfile"]
        file.libs = ["vorbisfile"]
        file.set_property("cmake_target_name", "Vorbis::vorbisfile")
        file.set_property("pkg_config_name", "vorbisfile")
        file.requires = ["vorbis"]
