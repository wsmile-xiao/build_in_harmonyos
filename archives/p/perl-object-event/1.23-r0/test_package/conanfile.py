#!/usr/bin/env python3
"""Conan test_package — Perl module L1 test.

Tests that Object::Event can be loaded and used.
"""
from conan import ConanFile


class PerlobjecteventTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        self.run("bash test_object_event.sh", env="conanrun")
