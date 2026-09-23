#!/usr/bin/env python3
"""open62541 1.5.7 — Conan test_package (consumer verification).

HarmonyOS 专项: builds a real consumer executable against the packaged
library and runs it as a functional test — an in-process UA_Server
publishes a variable node, a UA_Client connects over opc.tcp loopback
and verifies read / write / readback through the packaged
libopen62541.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Open62541TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the packaged-library functional test binary (server + client
        # over opc.tcp loopback) produced by build().
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_open62541_ohos"),
                 env="conanrun")
