#!/usr/bin/env python3
"""Conan recipe for the zfp 1.0.1 C compression library."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ZfpConan(ConanFile):
    name = "zfp"
    version = "1.0.1"
    description = "Fixed- and variable-rate compressed floating-point arrays"
    license = "BSD-3-Clause"
    homepage = "https://github.com/LLNL/zfp"
    url = "https://github.com/LLNL/zfp"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("zfp 1.0.1 supports Linux and OHOS in this recipe")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload URL 没有文件扩展名，显式指定归档格式供 Conan 解包。
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="zfp-1.0.1.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.cache_variables["ZFP_ENABLE_PIC"] = bool(self.options.get_safe("fPIC", True))
        tc.cache_variables["ZFP_WITH_OPENMP"] = False

        # Package the core C library.  The optional language bindings, CFP
        # library, examples, utilities, and full test suite pull in extra
        # toolchains or network-fetched projects that are outside this recipe.
        tc.cache_variables["BUILD_CFP"] = False
        tc.cache_variables["BUILD_ZFORP"] = False
        tc.cache_variables["BUILD_ZFPY"] = False
        tc.cache_variables["BUILD_UTILITIES"] = False
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_TESTING"] = True
        tc.cache_variables["BUILD_TESTING_FULL"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.run("ctest --output-on-failure", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["zfp"]
        self.cpp_info.set_property("cmake_file_name", "zfp")
        self.cpp_info.set_property("cmake_target_name", "zfp::zfp")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
