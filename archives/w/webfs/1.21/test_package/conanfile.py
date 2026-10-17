#!/usr/bin/env python3
"""Conan test recipe for webfs 1.21 (GNU make)."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class WebfsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            raise RuntimeError("webfs 1.21 consumer tests must run on HarmonyOS target")

        package = self.dependencies["webfs"]
        webfsd = os.path.join(package.package_folder, "bin", "webfsd")
        command = "python3 test_webfs.py --webfsd {} --openssl openssl --target-os {}".format(
            shlex.quote(webfsd),
            shlex.quote(str(self.settings.os)),
        )
        self.run(command, env="conanrun")
