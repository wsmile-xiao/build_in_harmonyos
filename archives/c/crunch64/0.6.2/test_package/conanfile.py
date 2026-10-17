#!/usr/bin/env python3
"""crunch64 CMake tests of the installed C archive and headers."""
import json
import os
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class Crunch64TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self, generator="Ninja")
        toolchain.generate()
        VirtualRunEnv(self).generate()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmp)
        env.vars(self, scope="run").save_script("crunch64_test")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration("Run this test_package on native HarmonyOS PC")
        command = "ctest --output-on-failure --no-tests=error --output-junit results.xml"
        self.run(command, env=["conanrun", "crunch64_test"])
        cases = ET.parse(os.path.join(self.build_folder, "results.xml")).findall(".//testcase")
        expected = {"consumer_yaz0", "consumer_yay0", "consumer_mio0", "consumer_errors",
                    "consumer_gzip", "harmonyos_deviceinfo_mmap"}
        if len(cases) != len(expected) or {case.get("name") for case in cases} != expected:
            raise ConanException("All six consumers, including the HarmonyOS test, must execute")
        if any(case.find("failure") is not None or case.find("skipped") is not None or
               case.find("error") is not None for case in cases):
            raise ConanException("A consumer test failed or was skipped")
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True, "passed": True, "command": command,
            "discovered": len(cases), "passedCount": len(cases), "failed": 0, "skipped": 0}))
