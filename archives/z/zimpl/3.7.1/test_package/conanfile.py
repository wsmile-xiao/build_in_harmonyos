#!/usr/bin/env python3
"""Conan test_package for zimpl 3.7.1 — Conan L1 consumer test.

Runs test.sh with bash; test.sh really executes the installed zimpl binary
on a small 0/1 knapsack model and asserts the produced .lp contains
Maximize/Subject to sections (R34: not a print-only stub). zimpl ships the
LP/MIP output backends only in the bin/zimpl executable — libzimpl.a
contains the parser core, so the executable is the consumer artifact.
"""
import os

from conan import ConanFile


class ZimplTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries reliably,
        # so wrap the test driver in bash (profile provides CONFIG_SHELL).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        self.run(f'{bash} test.sh "{pkg_folder}"', env="conanrun")
