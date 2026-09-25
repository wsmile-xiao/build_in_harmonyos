#!/usr/bin/env python3
"""Conan test_package for since — runs the packaged binary (R34).

The upstream tarball ships no test suite at all, so this test_package
re-implements the functional assertions of the Debian autopkgtest
(`debian/tests/simple`) against the packaged `since` executable:
  -z discards existing content, default action prints appended lines,
  truncation is detected and reported, and multi-file headers are emitted.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class SinceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bindirs = self.dependencies[self.tested_reference_str].cpp_info.bindirs
        bindir = bindirs[0] if bindirs else ""
        script = os.path.join(self.source_folder, "test_since.py")
        self.run(f'python3 "{script}" "{bindir}"', env="conanrun")
