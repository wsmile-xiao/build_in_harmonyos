#!/usr/bin/env python3
"""Consumer test recipe for cpufrequtils 008."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class CpufrequtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            self.output.info("cpufrequtils consumer test skipped: target cannot run")
            return

        dep = self.dependencies["cpufrequtils"]
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = compilers.get("c", "clang")

        script = os.path.join(self.recipe_folder, "test_cpufrequtils.py")
        self.run(
            '"{py}" "{script}" "{pkg}" "{work}" "{cc}"'.format(
                py=sys.executable,
                script=script,
                pkg=dep.package_folder,
                work=self.build_folder,
                cc=cc,
            ),
            env="conanrun",
        )
