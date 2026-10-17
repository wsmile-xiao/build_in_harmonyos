#!/usr/bin/env python3
"""test_package for esekeyd — exercises the installed binaries as a consumer.

esekeyd/keytest/learnkeys need a real /dev/input event device to daemonize,
so the consumer test verifies everything that does not require hardware:
usage/error paths of all three programs, and — the core of the package —
the parse() key mapping, by replaying synthetic binary input_event records
through keytest (it accepts any readable file as its device argument).
"""
import os

from conan import ConanFile


class EsekeydTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap in bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
