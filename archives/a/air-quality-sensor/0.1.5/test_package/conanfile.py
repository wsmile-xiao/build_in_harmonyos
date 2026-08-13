#!/usr/bin/env python3
"""Conan test_package for air-quality-sensor 0.1.5 — runs the packaged CLI.

air-quality-sensor is a command-line tool (no library to link): the consumer
test executes the packaged binary with --version / --help / bare run and
verifies real output (R34 — the binary IS the tested API).
"""

import os

from conan import ConanFile


class AirQualitySensorTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution (aa3d precedent).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_air_quality_sensor.sh", env="conanrun")
