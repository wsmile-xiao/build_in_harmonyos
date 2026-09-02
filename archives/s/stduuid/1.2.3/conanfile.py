#!/usr/bin/env python3
"""Conan recipe for stduuid 1.2.3 (header-only CMake INTERFACE library).

Upstream: https://github.com/mariusbancila/stduuid
Build: CMake INTERFACE target, installs include/uuid.h and (unless C++20 span
is selected) the bundled gsl/ headers. No compiled artifacts.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class StduuidConan(ConanFile):
    name = "stduuid"
    version = "1.2.3"
    description = "A C++17 cross-platform library for generating and parsing UUIDs (header-only)."
    license = "MIT"
    homepage = "https://github.com/mariusbancila/stduuid"
    url = "https://github.com/mariusbancila/stduuid"

    # Header-only INTERFACE library -> no compiled artifacts.
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # codeload 的 tar.gz 直链以 /refs/tags/v1.2.3 结尾，无文件扩展名；
        # 显式指定 filename 为 .tar.gz，否则 conan 按 zip 解压报 BadZipFile。
        get(self, **self.conan_data["sources"], filename="stduuid-1.2.3.tar.gz",
            strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Do not build upstream unit tests inside the package; provide only the
        # interface target + installed headers (tests run via test_package).
        tc.variables["UUID_BUILD_TESTS"] = "OFF"
        tc.variables["UUID_ENABLE_INSTALL"] = "ON"
        # Upstream default: UUID_USING_CXX20_SPAN=OFF -> also installs gsl/ span
        # headers so C++17 consumers (OHOS default) can include <gsl/span>.
        tc.variables["UUID_USING_CXX20_SPAN"] = "OFF"
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
        self.cpp_info.set_property("cmake_file_name", "stduuid")
        self.cpp_info.set_property("cmake_target_name", "stduuid::stduuid")
        self.cpp_info.includedirs = ["include"]
        # Header-only: no libraries to link.
        self.cpp_info.libs = []
