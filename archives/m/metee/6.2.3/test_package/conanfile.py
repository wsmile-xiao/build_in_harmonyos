#!/usr/bin/env python3
"""Conan test_package for metee 6.2.3.

Compiles and runs a tiny program against the installed libmetee: it calls
TeeInit() and expects either a successful MEI connection or TEE_DEVICE_NOT_FOUND
(no Intel MEI device is expected in the test environment).
"""
import json
import os

from conan import ConanFile


class MeteeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dependency = self.dependencies[self.tested_reference_str]
        includedir = os.path.join(dependency.package_folder,
                                  dependency.cpp_info.includedirs[0])
        libdir = os.path.join(dependency.package_folder,
                              dependency.cpp_info.libdirs[0])
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = executables.get("c") or "clang"
        source = os.path.join(self.recipe_folder, "test_metee.c")
        self.run('"{}" -I"{}" "{}" -L"{}" -lmetee -o test_metee'.format(
            cc, includedir, source, libdir))

    def test(self):
        self.run("./test_metee")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "./test_metee (TeeInit)",
            "consumer_passed": 1,
            "consumer_total": 1,
        }))
