#!/usr/bin/env python3
"""Consumer test for rungetty: executes the packaged binary (R34).

Nothing is compiled here — rungetty is an application package whose only
dependency is libc, so the test drives the installed executable and inspects the
installed manual page.  `can_run()` is deliberately *not* used as an early
return: when the package artifacts are missing the test must fail (CI gate L1e
removes bin/ and re-runs this test to prove the dependency is real).
"""
import os
import sys

from conan import ConanFile


class RungettyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        executable = os.path.join(dep.package_folder, "bin", "rungetty")
        script = os.path.join(self.recipe_folder, "test_rungetty.py")
        self.run(
            f'"{sys.executable}" "{script}" "{executable}" "{dep.package_folder}"',
            env="conanrun",
        )
