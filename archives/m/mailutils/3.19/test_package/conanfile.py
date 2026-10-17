#!/usr/bin/env python3
"""Conan test_package for GNU Mailutils 3.19 (HarmonyOS PC).

Two levels:
  * `test_mailutils.c` — consumer test: links libmailutils and exercises the
    public list/url/locker API (the locker check covers the OHOS-specific
    hard-link-free dotlock path).
  * `test_ohos_mailutils.sh` — HarmonyOS-specific test: platform identity,
    CLI/server smoke test and reported version.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MailutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        cmake = CMake(self)
        cmake.test()
        binary = os.path.join(self.cpp.build.bindirs[0], "test_mailutils")
        self.run('"%s"' % binary, env="conanrun")
        package = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "test_ohos_mailutils.sh")
        self.run('sh "%s" "%s"' % (script, package), env="conanrun")
