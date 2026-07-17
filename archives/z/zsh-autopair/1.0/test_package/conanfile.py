#!/usr/bin/env python3
"""Conan test_package — zsh-autopair 1.0 smoke test"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class ZshAutopairTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building; skipping runtime Zsh smoke test")
            return

        dep = self.dependencies["zsh-autopair"]
        plugin = os.path.join(dep.package_folder, "share", "zsh-autopair", "autopair.zsh")
        if not os.path.isfile(plugin):
            raise Exception(f"Missing plugin file: {plugin}")

        zsh = shutil.which("zsh")
        if not zsh:
            self.output.warning("zsh not found; file layout check completed")
            return

        zsh_script = f"source {shlex.quote(plugin)}; [[ -n $AUTOPAIR_PAIRS ]]"
        self.run(f"{shlex.quote(zsh)} -fc {shlex.quote(zsh_script)}", env="conanrun")