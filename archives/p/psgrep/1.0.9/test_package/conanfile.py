#!/usr/bin/env python3
"""Conan test_package — psgrep 1.0.9

Runs the packaged psgrep command and verifies version/help output plus real process
search behavior from a consumer package.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class PsgrepTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _bash(self):
        for candidate in (os.environ.get("CONFIG_SHELL"), shutil.which("bash"), "/data/service/hnp/bin/bash", os.environ.get("SHELL")):
            if candidate and os.path.exists(candidate):
                return candidate
        return "bash"

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["psgrep"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        psgrep = os.path.join(bin_dir, "psgrep")
        bash = self._bash()
        env_path = f"{bin_dir}:$PATH"

        self.run(f'PATH="{env_path}" "{bash}" "{self.source_folder}/test.sh"', env="conanrun")

        version = subprocess.run(
            [bash, psgrep, "-v"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if version.returncode != 2 or "psgrep version 1.0.9" not in version.stdout:
            raise RuntimeError("psgrep -v did not report version 1.0.9 with upstream exit status 2")

        search = subprocess.run(
            [bash, psgrep, "-n", "-s", "python"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if search.returncode != 0:
            raise RuntimeError("psgrep -n -s python failed")

        pid_search = subprocess.run(
            [bash, psgrep, "-d", "python"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if pid_search.returncode != 0:
            raise RuntimeError("psgrep -d python failed")
        if pid_search.stdout.strip():
            for line in pid_search.stdout.splitlines():
                if line.strip() and not line.strip().isdigit():
                    raise RuntimeError(f"psgrep -d emitted a non-PID line: {line}")
