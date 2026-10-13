#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/build2/{version}/test_package/conanfile.py
"""
from conan import ConanFile
from conan.tools.build import can_run
import os
import shlex
import sys


class Build2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        pass

    def test(self):
        binary = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                              "bin", "build2")
        if not os.path.isfile(binary):
            raise RuntimeError("tested package lacks bin/build2")
        if not can_run(self):
            self.output.warning("Target execution unavailable; no runtime PASS claimed")
            return
        self.run(shlex.quote(binary) + " --version", env="conanrun")
        print("CONSUMER_TEST_PASS=1/1")
        if str(self.settings.os) == "OHOS":
            driver = os.path.join(self.source_folder, "harmony_tests", "hmdfs_testscript.py")
            self.run(" ".join(shlex.quote(x) for x in [sys.executable, driver, binary,
                          self.build_folder]), env="conanrun")
