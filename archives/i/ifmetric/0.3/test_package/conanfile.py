#!/usr/bin/env python3
"""Consumer test for the packaged ifmetric executable.

Runs the real binary and asserts its rtnetlink behaviour, not just that a file
exists. See smoke.sh for why every invocation is constructed so that no route
can possibly be mutated.
"""
import os
import shutil

from conan import ConanFile


class IfmetricTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "smoke.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["ifmetric"].package_folder
        executable = None
        for bindir in ("bin", "sbin"):
            candidate = os.path.join(package_folder, bindir, "ifmetric")
            if os.path.isfile(candidate):
                executable = candidate
                break
        if executable is None:
            raise Exception(f"no ifmetric executable found under {package_folder}")
        self.output.info(f"Testing consumer binary: {executable}")

        script = os.path.join(self.source_folder, "smoke.sh")
        shell = shutil.which("sh") or "/bin/sh"
        # Deliberately not gated on can_run(): the build runs on the HarmonyOS PC
        # itself, so the produced ELF is natively executable here.
        self.run(f'"{shell}" "{script}" "{executable}"', env="conanrun")
