#!/usr/bin/env python3
"""Conan CMake recipe for libmdbx 0.14.3."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibmdbxConan(ConanFile):
    name = "libmdbx"
    version = "0.14.3"
    description = "Embedded transactional key-value database engine"
    license = "Apache-2.0"
    homepage = "https://github.com/erthink/libmdbx"
    url = "https://github.com/erthink/libmdbx"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libmdbx 0.14.3 supports Linux and OHOS in this recipe")
        check_min_cppstd(self, 11)

    def requirements(self):
        # libmdbx only needs the platform thread library.
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # Conan 2.29.1 maps OHOS to HarmonyOS, while this CMake release
            # provides the platform module under the OHOS name.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            # HMDFS returns EACCES from posix_fallocate(), while the same
            # file accepts pwrite()/ftruncate(). Use the latter path in
            # osal_fsetsize() so a new environment can be opened on OHOS.
            tc.variables["MDBX_USE_FALLOCATE"] = False

        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["MDBX_BUILD_SHARED_LIBRARY"] = bool(self.options.shared)
        tc.variables["MDBX_INSTALL_STATIC"] = not bool(self.options.shared)
        tc.variables["MDBX_BUILD_TOOLS"] = False
        tc.variables["MDBX_INSTALL_MANPAGES"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["MDBX_ENABLE_TESTS"] = False
        tc.variables["MDBX_BUILD_CXX"] = True
        tc.variables["MDBX_C_STANDARD"] = 11
        tc.variables["MDBX_CXX_STANDARD"] = 17
        tc.variables["MDBX_BUILD_TIMESTAMP"] = "unknown"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True)) or bool(
            self.options.shared
        )
        if self.options.shared:
            tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
            tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        for license_file in ("LICENSE", "NOTICE", "COPYRIGHT"):
            copy(self, license_file, src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        CMake(self).install()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["mdbx"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "libmdbx")
        self.cpp_info.set_property("cmake_target_name", "libmdbx::mdbx")
        self.cpp_info.set_property("pkg_config_name", "libmdbx")
