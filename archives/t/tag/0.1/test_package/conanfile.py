#!/usr/bin/env python3
"""Conan test_package for tag 0.1 — functional checks of the packaged CLI.

tag is a command-line tool (no library to link): the consumer test executes
the packaged `tag` binary with real stdin payloads and verifies real output
(message prefix, %l line counter, %d date stamp, usage exit code, invalid
format error path) — R34: the binary IS the tested API.
"""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class TagTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_tag.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            return
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably;
        # wrap the script in bash (aa3d / air-quality-sensor precedent).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_tag.sh", env="conanrun")
