#!/usr/bin/env python3
"""Consumer test for the packaged ifplugd executables.

Runs the real binaries and asserts their option-parser behaviour, not just
that files exist. See smoke.sh for the assertion list (6 assertions).
"""
import os
import shutil

from conan import ConanFile


class IfplugdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "smoke.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_binary(self, name):
        pkg = self.dependencies["ifplugd"].package_folder
        for bindir in ("bin", "sbin"):
            candidate = os.path.join(pkg, bindir, name)
            if os.path.isfile(candidate):
                return candidate
        raise Exception(f"no {name} executable found under {pkg}")

    def test(self):
        ifplugd = self._find_binary("ifplugd")
        ifplugstatus = self._find_binary("ifplugstatus")
        self.output.info(f"Testing consumer binaries: {ifplugd}, {ifplugstatus}")
        script = os.path.join(self.source_folder, "smoke.sh")
        shell = shutil.which("sh") or "/bin/sh"
        # Build runs natively on HarmonyOS PC, so the ELF is directly runnable.
        self.run(f'"{shell}" "{script}" "{ifplugd}" "{ifplugstatus}"', env="conanrun")
        self.output.info("ifplugd consumer behavior test: 6/6 assertions passed")
