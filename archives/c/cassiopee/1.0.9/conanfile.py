#!/usr/bin/env python3
"""Conan recipe — Cassiopee 1.0.9 (CMake)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CassiopeeConan(ConanFile):
    name = "cassiopee"
    version = "1.0.9"
    description = "C++ genomic sequence indexing and search library"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/osallou/cassiopee-c"
    url = "https://github.com/osallou/cassiopee-c"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.90.0.4")
        self.requires("glog/0.7.1")

    def build_requirements(self):
        self.test_requires("cppunit/1.15.1")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["Boost_NO_SYSTEM_PATHS"] = True
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.requires = [
            "boost::boost",
            "boost::serialization",
            "glog::glog",
        ]
        self.cpp_info.libs = ["cassie"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "cassiopee")
        self.cpp_info.set_property("cmake_target_name", "cassiopee::cassiopee")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
