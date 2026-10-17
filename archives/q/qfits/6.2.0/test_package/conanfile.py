#!/usr/bin/env python3
"""Conan test_package for qfits 6.2.0.

Compiles and runs a tiny program against the installed libqfits: it includes
the public <qfits.h> and calls qfits_version().
"""
import json
import os

from conan import ConanFile


class QfitsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
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
        source = os.path.join(self.recipe_folder, "test_qfits.c")
        self.run('"{}" -I"{}" "{}" -L"{}" -lqfits -lm -o test_qfits'.format(
            cc, includedir, source, libdir))

    def test(self):
        self.run("./test_qfits", env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "./test_qfits (qfits_version)",
            "consumer_passed": 1,
            "consumer_total": 1,
        }))
