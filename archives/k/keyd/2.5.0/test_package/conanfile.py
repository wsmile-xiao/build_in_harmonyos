#!/usr/bin/env python3
"""test_package for keyd 2.5.0 -- consumer test of the installed daemon binary."""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException


class KeydTestConan(ConanFile):
    """Builds the kernel-interface probe and drives the packaged keyd through it."""

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        """Same resolution order as the recipe: the profile value is trusted only after
        an X_OK probe -- the visibility of /data/service/hnp/* varies with the device
        state (it was unreachable in a pre-reboot session and is what the profile
        resolves to now), so no absolute tool path may be assumed."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        home_clang = os.path.expanduser("~/usr/local/bin/clang")
        for cand in ((compilers or {}).get("c"), shutil.which("clang"),
                     shutil.which("cc"), home_clang):
            if cand and os.access(cand, os.X_OK):
                return cand
        raise ConanException("no executable C compiler for the keyd interface probe")

    def build(self):
        self.run(
            '"{cc}" -O1 -o "{out}" "{src}"'.format(
                cc=self._cc(),
                out=os.path.join(self.build_folder, "probe_input"),
                src=os.path.join(self.recipe_folder, "probe_input.c"),
            )
        )

    def test(self):
        pkg_folder = self.dependencies["keyd"].package_folder
        script = os.path.join(self.recipe_folder, "test_keyd.py")
        probe = os.path.join(self.build_folder, "probe_input")
        self.run(
            '"{py}" "{script}" "{pkg}" "{probe}"'.format(
                py=sys.executable, script=script, pkg=pkg_folder, probe=probe
            ),
            env="conanrun",
        )
