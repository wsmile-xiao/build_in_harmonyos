#!/usr/bin/env python3
"""Conan recipe for docopt.cpp 0.6.3."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class DocoptCppConan(ConanFile):
    name = "docopt.cpp"
    version = "0.6.3"
    description = "C++11 port of docopt"
    license = "MIT, BSL-1.0"
    homepage = "https://github.com/docopt/docopt.cpp"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["WITH_TESTS"] = "ON"
        tc.variables["WITH_EXAMPLE"] = "ON"
        tc.variables["USE_BOOST_REGEX"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        executable = os.path.join(self.build_folder, "docopt_example")
        # 上游 CMakeLists 用 configure_file 把 run_tests.py 替换占位符后输出为
        # ${CMAKE_CURRENT_BINARY_DIR}/run_tests（无扩展名），即 build_folder/run_tests。
        runner = os.path.join(self.build_folder, "run_tests")
        if self.settings.os in ("Linux", "OHOS"):
            runtime_env = f'LD_LIBRARY_PATH="{self.build_folder}"'
            self.run(
                f'{runtime_env} "{executable}" '
                "ship Guardian move 10 20 --speed=7"
            )
            self.run(f'{runtime_env} python3 "{runner}"')
        else:
            self.run(f'"{executable}" ship Guardian move 10 20 --speed=7')
            self.run(f'python3 "{runner}"')

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["docopt"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "docopt")
        self.cpp_info.set_property("cmake_target_name", "docopt::docopt")
        self.cpp_info.set_property("pkg_config_name", "docopt")
