#!/usr/bin/env python3
"""test_package for utmps: links libutmps and calls its API, then asserts on the
delivered program's usage text. Both steps fail the test on unmet expectations."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class UtmpsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # In a test_package, self.package_folder is the *test* package's folder;
        # the tested content lives under the dependency's folder.
        dep = self.dependencies["utmps"]
        candidates = [os.path.join(dep.package_folder, d, "utmps-write")
                      for d in (dep.cpp_info.bindirs or ["bin"])]
        candidates.append(os.path.join(dep.package_folder, "sbin", "utmps-write"))
        binary = next((c for c in candidates if os.path.isfile(c)), None)
        if not binary:
            raise ConanException("utmps-write not found under %s (looked at %s)"
                                 % (dep.package_folder, candidates))
        script = os.path.join(self.source_folder, "smoke-cli.sh")
        # R34/L0d: the compiled consumer is executed, not merely built.
        self.run("./test_utmps", env="conanrun")
        self.run("sh %s %s" % (script, binary), env="conanrun")
