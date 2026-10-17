#!/usr/bin/env python3
"""test_package for jamnntpd 1.3 — runs the loopback NNTP consumer test script."""
import os
import shutil

from conan import ConanFile


class JamnntpdTestConan(ConanFile):
    """Executable package: test() delegates to test_script.py via self.run()."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        pkg = self.dependencies["jamnntpd"].package_folder
        script = os.path.join(self.recipe_folder, "test_script.py")
        python3 = shutil.which("python3") or shutil.which("python")
        assert python3, "need python3 on PATH for the NNTP consumer test"
        # conanrun env puts the package bin/ on PATH; pkg is passed for the
        # direct-path fast lane.
        self.run(f'"{python3}" "{script}" "{pkg}"', env="conanrun")
