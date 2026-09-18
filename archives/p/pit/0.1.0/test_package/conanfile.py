#!/usr/bin/env python3
"""Conan test_package for pit 0.1.0 — CLI functional test.

L1 test: run test.sh against the installed pit binary. test.sh exercises
the real project/task/note/log/info lifecycle with PITFILE isolation and
emits the HMBS evidence markers.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["pit"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            pit_cmd = os.path.join(bin_dir, "pit")

            # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
            # Use bash to wrap binary execution.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

            self.run(f'{bash} test.sh "{pit_cmd}"', env="conanrun")
