#!/usr/bin/env python3
"""Conan test_package for ruby — L1 smoke test (R34: real dependency usage).

Ruby is an interpreter, so the L1 test runs the installed `ruby` binary
end-to-end: version check + loading the OpenSSL/YAML/Fiddle extensions
(dependencies declared in the recipe) and executing a real program.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class RubyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: ruby runtime smoke skipped")
            return

        script = os.path.join(self.source_folder, "test_ruby.sh")
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} {script}", env="conanrun")
