#!/usr/bin/env python3
"""Conan recipe for QuantLib 1.43."""

import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class QuantLibConan(ConanFile):
    name = "quantlib"
    version = "1.43"
    description = "A free/open-source library for quantitative finance"
    license = "BSD-3-Clause"
    homepage = "https://www.quantlib.org/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("boost/1.84.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS Boost.Math long double promotion is flaky on the failing root-finding path.
        tc.preprocessor_definitions["BOOST_MATH_PROMOTE_DOUBLE_POLICY"] = "0"
        # boost 1.84 sp_thread_sleep.hpp uses pthread_setcancelstate on
        # non-Android PTHREAD builds; OHOS lacks that symbol.
        tc.preprocessor_definitions["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"] = "1"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["QL_BUILD_EXAMPLES"] = "OFF"
        tc.variables["QL_BUILD_TEST_SUITE"] = "ON"
        tc.variables["QL_BUILD_FUZZ_TEST_SUITE"] = "OFF"
        tc.variables["QL_INSTALL_EXAMPLES"] = "OFF"
        tc.variables["QL_INSTALL_TEST_SUITE"] = "OFF"
        tc.variables["QL_INSTALL_BENCHMARK"] = "OFF"
        tc.variables["QL_ENABLE_OPENMP"] = "OFF"
        tc.variables["QL_ENABLE_DEFAULT_WARNING_LEVEL"] = "OFF"
        tc.variables["QL_COMPILE_WARNING_AS_ERROR"] = "OFF"
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

        test_binary = os.path.join(self.build_folder, "test-suite", "quantlib-test-suite")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Static build: test-suite links libQuantLib.a directly.
        self.run(
            f"{shlex.quote(bash)} -c {shlex.quote(shlex.quote(test_binary))}",
            env=["conanbuild", "conanrun"],
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["QuantLib"]
        self.cpp_info.set_property("cmake_file_name", "QuantLib")
        self.cpp_info.set_property("cmake_target_name", "QuantLib::QuantLib")
