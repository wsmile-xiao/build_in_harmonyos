#!/usr/bin/env python3
"""Conan test_package for iniparser 4.2.6 — consumer API round-trip test.

R34: the test executable calls the real iniparser public API
(iniparser_load/getstring/getint/getboolean/set/getnsec/getsecname/
getsecnkeys/freedict) over a generated INI file, performing a full
read/write round-trip.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class IniparserTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_binary = os.path.join(self.build_folder, "test_iniparser")
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        self.run(
            f"{shlex.quote(bash)} -c {shlex.quote(shlex.quote(test_binary))}",
            env="conanrun",
            cwd=self.build_folder,
        )
