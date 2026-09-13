#!/usr/bin/env python3
"""Conan test package for paho.mqtt.cpp 1.6.0."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PahoMqttCppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Keep the consumer build compatible with the OHOS filesystem's
        # lack of GNU make jobserver FIFO support.
        if str(self.settings.os) == "OHOS":
            self.conf.define("tools.build:jobs", 1)
        cmake.build()

    def test(self):
        test_names = ["test_paho_mqtt_cpp"]
        if str(self.settings.os) == "OHOS":
            test_names.append("test_paho_mqtt_cpp_ohos")
        for test_name in test_names:
            cmd = os.path.join(self.cpp.build.bindirs[0], test_name)
            self.run(cmd, env="conanrun")
