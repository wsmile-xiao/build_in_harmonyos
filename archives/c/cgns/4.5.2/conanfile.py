#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CgnsConan(ConanFile):
    name = "cgns"
    version = "4.5.2"
    description = "CFD General Notation System"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/CGNS/CGNS"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CGNS_ENABLE_HDF5"] = False
        # 启用上游测试（CTest）并拷贝测试数据，conan create 时执行上游 C 测试
        tc.variables["CGNS_ENABLE_TESTS"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 执行上游 CTest（C 测试 23/23 通过 + 1 skip，0 失败；Fortran 因无编译器 N/A）
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["cgns"]
