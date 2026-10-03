#!/usr/bin/env python3
"""test_package for plink 1.07 — delegates to test_plink.py via self.run().

The tests execute the packaged aarch64/musl `plink` binary itself (real
analysis runs on the upstream example dataset), so this test fails if the
package is empty or the binary cannot run.
"""
import os
import shutil

from conan import ConanFile


class PlinkTestConan(ConanFile):
    """Executable package: test() delegates to test_plink.py via self.run()."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        pkg = self.dependencies["plink"].package_folder
        script = os.path.join(self.recipe_folder, "test_plink.py")
        python3 = shutil.which("python3") or shutil.which("python")
        assert python3, "need python3 on PATH for the plink consumer tests"
        # conanrun env puts the package bin/ on PATH; the package folder is
        # also passed explicitly so the tests can reach share/plink/.
        self.run(f'"{python3}" "{script}" "{pkg}"', env="conanrun")
