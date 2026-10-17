#!/usr/bin/env python3
"""test_package for memlockd 1.3.1 -- runs the packaged daemon as an unprivileged user."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class MemlockdTest(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "memlockd test_package must run on the target device (cross build cannot exec it)")
        pkg = self.dependencies["memlockd"].package_folder
        script = os.path.join(self.recipe_folder, "test_memlockd.py")
        # Scratch data (an 8 MiB mlock target plus generated configs) must not
        # land inside the tracked archives/ tree: test_package has no layout()
        # override here, so build_folder resolves to the recipe directory.
        work = os.path.join(self.build_folder, "mlk-work")
        # The daemon binary itself is exercised inside the suite (it cannot be probed
        # with --help here: memlockd has no version option), so this single entry
        # point is the real consumer path.
        try:
            self.run(f'python3 "{script}" "{pkg}" "{work}"', env="conanrun")
        finally:
            # Kill-safe cleanup: the suite only unlinks its large file on the
            # happy path, so the caller owns the directory removal.
            shutil.rmtree(work, ignore_errors=True)
