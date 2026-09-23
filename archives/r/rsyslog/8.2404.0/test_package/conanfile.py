#!/usr/bin/env python3
"""Conan test_package — rsyslog 8.2404.0 (rsyslogd daemon).

Verifies the rsyslogd binary is installed and can report its version.
"""
from conan import ConanFile
from conan.tools.build import can_run


class RsyslogTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("bash test.sh", env="conanrun")
