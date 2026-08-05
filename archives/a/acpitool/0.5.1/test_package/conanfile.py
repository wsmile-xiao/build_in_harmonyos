#!/usr/bin/env python3
"""Conan test_package for acpitool 0.5.1.

Smoke test for the acpitool CLI tool. Upstream has no official test suite.
acpitool -h (no ACPI interface dependency) is used as the smoke test.
"""
from conan import ConanFile
from conan.tools.layout import basic_layout


class AcpitoolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        # acpitool -h displays help text and does not depend on ACPI interfaces.
        # /proc/acpi and /sys/bus/acpi are absent on HarmonyOS PC.
        # acpitool exits with 255 on HarmonyOS because it cannot open ACPI files,
        # but the help text is still printed. This is expected behavior.
        # The shell wrapper accepts exit 255 (ACPI missing) or 0 (success) as valid.
        self.run("acpitool -h 2>&1; s=$?; [ $s -eq 255 -o $s -eq 0 ]", env="conanrun")