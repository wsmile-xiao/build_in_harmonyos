#!/usr/bin/env python3
"""Conan test_package for pth 2.0.7.

Compiles and runs a tiny program against the installed libpth: it initialises
the Pth scheduler, spawns a cooperative thread, joins it and checks the return
value.  This exercises the machine-context (mctx) switch at runtime.
"""
import json
import os

from conan import ConanFile


class PthTestConan(ConanFile):
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
        source = os.path.join(self.recipe_folder, "test_pth.c")
        self.run('"{}" -I"{}" "{}" -L"{}" -lpth -ldl -lm -o test_pth'.format(
            cc, includedir, source, libdir))

    def test(self):
        self.run("./test_pth")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "./test_pth (pth_init + pth_spawn + pth_join)",
            "consumer_passed": 1,
            "consumer_total": 1,
        }))
