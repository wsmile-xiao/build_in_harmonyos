#!/usr/bin/env python3
"""Installed-package consumer test for wmcdplay 1.1.

The recipe builds an X11 client executable, so the consumer view is the
installed package: the ``wmcdplay`` ELF, its runtime dependency contract, the
installed artwork data and the manual page.  The behavioural part runs the real
binary; ``--help`` is answered by ``scanArgs()`` before ``initXWin()`` touches
the X server, so the whole consumer test is display-independent and can run on a
headless HarmonyOS PC worker.
"""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class WmcdplayTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # The package ships an executable: on a worker that cannot run the
        # target the consumer test would silently degrade into a no-op, which
        # is exactly what R51/L1 forbids, so refuse instead of skipping.
        if not can_run(self):
            raise ConanException(
                "wmcdplay consumer test requires an executable HarmonyOS target; "
                f"cannot run {self.settings.os}/{self.settings.arch} binaries here"
            )

        package = self.dependencies["wmcdplay"].package_folder
        script = os.path.join(self.recipe_folder, "test_wmcdplay.py")
        self.run(
            f'"{sys.executable}" "{script}" "{package}"',
            env="conanrun",
        )
