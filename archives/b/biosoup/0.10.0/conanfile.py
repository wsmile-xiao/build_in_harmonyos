import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class BiosoupConan(ConanFile):
    name = "biosoup"
    version = "0.10.0"
    description = "C++11 header-only collection of data structures for storage and logging in bioinformatics tools"
    license = "MIT"
    homepage = "https://github.com/rvaser/biosoup"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游单元测试依赖 GoogleTest（abseil/20260526 先例：test_requires 不入下游闭包）
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["biosoup_install"] = False
        tc.variables["biosoup_build_tests"] = True
        # 直接命中 conan 缓存中 gtest 的 CMake config（abseil 先例同款）
        gtest = self.dependencies.get("gtest")
        if gtest:
            tc.variables["GTest_DIR"] = os.path.join(
                gtest.package_folder, "lib", "cmake", "GTest")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst="licenses")
        copy(self, "*.hpp", src=f"{self.source_folder}/include/biosoup",
             dst=f"{self.package_folder}/include/biosoup")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "biosoup")
        self.cpp_info.set_property("cmake_target_name", "biosoup::biosoup")
