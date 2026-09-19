#!/usr/bin/env python3
"""Conan test_package for perl-pod-parser 1.67 — runs the R34 consumer check.

Runs a Python script that exercises the packaged Pod::* modules through the
perl interpreter (same approach as this archive's perl-carp test_package):
parse a real POD document via a Pod::Parser subclass, extract sections with
Pod::Select::podselect, and inspect Pod::Find — real API usage rather than a
file-presence-only check.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("cannot run on this platform")
        pkg = self.dependencies["perl-pod-parser"].package_folder
        perl5 = os.path.join(pkg, "lib", "perl5")
        if not os.path.isdir(os.path.join(perl5, "Pod")):
            raise ConanException(f"Pod/ modules missing under {perl5}")
        test_script = os.path.join(os.path.dirname(__file__), "test_pod_parser.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_pod_parser.py missing: {test_script}")
        self.run(f'{sys.executable} "{test_script}" "{pkg}"', env="conanrun")
