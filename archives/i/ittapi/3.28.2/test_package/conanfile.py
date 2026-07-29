#!/usr/bin/env python3
"""Exercise the packaged ittapi libraries and upstream C++ tests."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class IttapiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    _upstream_tests = (
        "test_string_handle",
        "test_domain",
        "test_task",
        "test_region",
        "test_frame",
        "test_collection_control",
        "test_thread_naming",
        "test_ittapi",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        package_folder = self.dependencies["ittapi"].package_folder
        upstream_dir = os.path.join(
            package_folder, "share", "ittapi", "upstream-tests"
        )
        for test_name in self._upstream_tests:
            self.run(os.path.join(upstream_dir, test_name), env="conanrun")
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_ittapi_consumer"),
            env="conanrun",
        )
