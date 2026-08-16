#!/usr/bin/env python3
"""Conan test package — activity-aware-firefox portable context provider."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class ActivityAwareFirefoxTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["activity-aware-firefox"]
        script = os.path.join(dep.package_folder, "bin", "activityfirefox")
        if not os.path.isfile(script):
            raise RuntimeError(f"Packaged wrapper is missing: {script}")
        if str(self.settings.os) == "OHOS" and os.name == "nt":
            self.output.info(
                "OHOS package was created on Windows; runtime test runs in OHOS CI."
            )
            return
        if not can_run(self):
            self.output.info("Cross-packaged script; runtime test runs in OHOS CI.")
            return
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        # System32/bash.exe is only the WSL launcher, not a POSIX shell.
        if shell and os.name == "nt" and os.path.basename(shell).lower() == "bash.exe":
            normalized = os.path.normcase(os.path.abspath(shell))
            windows_dir = os.path.normcase(os.environ.get("WINDIR", "C:\\Windows"))
            if normalized.startswith(windows_dir):
                shell = None
        if not shell:
            raise ConanInvalidConfiguration(
                "A real Bash executable is required; the Windows WSL launcher is not sufficient"
            )
        test_script = os.path.join(self.source_folder, "test_activity_context.sh")
        self.run(f'"{shell}" "{test_script}" "{script}"')
