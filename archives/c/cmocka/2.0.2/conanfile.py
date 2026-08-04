#!/usr/bin/env python3
"""Conan recipe for cmocka 2.0.2."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CMockaConan(ConanFile):
    name = "cmocka"
    version = "2.0.2"
    description = "C unit testing framework with mock object support"
    license = "Apache-2.0"
    homepage = "https://cmocka.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["WITH_EXAMPLES"] = "ON"
        tc.variables["UNIT_TESTING"] = "ON"
        tc.variables["PICKY_DEVELOPER"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.run('ctest -N --test-dir "{}"'.format(self.build_folder))
        self.run('ctest --test-dir "{}" --output-on-failure -j1'.format(self.build_folder))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cmocka")
        self.cpp_info.set_property("cmake_target_name", "cmocka::cmocka")
        self.cpp_info.set_property("cmake_config_version_compat", "AnyNewerVersion")
        self.cpp_info.set_property("pkg_config_name", "cmocka")
        self.cpp_info.libs = ["cmocka"]
