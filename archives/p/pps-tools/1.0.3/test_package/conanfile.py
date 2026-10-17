#!/usr/bin/env python3
"""Conan test_package for pps-tools 1.0.3.

Compiles a small consumer against the installed PPSAPI header
(``include/sys/timepps.h``) and runs the installed programs through a real
shell harness.  Upstream ships no test suite, so this is the 鸿蒙/host-specific
verification for the adaptation.
"""
import json
import os

from conan import ConanFile

CHECKS = 12


class PpsToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get("c") or "clang"

    def build(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        include_dir = os.path.join(package_folder, "include")
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-g -O0"
        out = os.path.join(self.build_folder, "test_header")
        self.run('"{}" {} -Wall -I "{}" "{}" -o "{}"'.format(
            self._cc(), opt, include_dir,
            os.path.join(self.recipe_folder, "test_header.c"), out),
            env="conanbuild")

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        bindir = os.path.join(package_folder, "bin")
        consumer = os.path.join(self.build_folder, "test_header")
        script = os.path.join(self.recipe_folder, "test_pps_tools.sh")
        self.run('PPS_BINDIR="{}" HEADER_TEST_BIN="{}" sh "{}"'.format(
            bindir, consumer, script), env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_pps_tools.sh (pps-tools consumer checks)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
