import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, mkdir


class Utf8procConan(ConanFile):
    name = "utf8proc"
    version = "2.11.3.3"
    description = "Clean C library for processing UTF-8 Unicode data"
    homepage = "https://github.com/JuliaStrings/utf8proc"
    license = "MIT"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("utf8proc supports OHOS armv8 only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        tc.cache_variables["UTF8PROC_ENABLE_TESTING"] = True
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        include_dir = os.path.join(self.package_folder, "include")
        lib_dir = os.path.join(self.package_folder, "lib")
        mkdir(self, include_dir)
        mkdir(self, lib_dir)
        copy(self, "utf8proc.h", dst=include_dir, src=self.source_folder, keep_path=False)
        copy(self, "libutf8proc.a", dst=lib_dir, src=self.build_folder, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["utf8proc"]
        self.cpp_info.set_property("cmake_file_name", "utf8proc")
        self.cpp_info.set_property("cmake_target_name", "utf8proc::utf8proc")
