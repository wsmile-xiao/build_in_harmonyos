#!/usr/bin/env python3
"""Conan test_package — prettyping 1.1.0.

Runs the packaged prettyping command with a deterministic mock ping command so
that the consumer test validates real CLI behavior without network/ICMP access.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class PrettypingTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        self.settings.rm_safe("os.version")

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            "/data/service/hnp/bin/bash",
            os.environ.get("SHELL"),
        ):
            if candidate and os.path.exists(candidate):
                return candidate
        return "bash"

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["prettyping"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        prettyping = os.path.join(bin_dir, "prettyping")
        bash = self._bash()
        bash_dir = os.path.dirname(bash)
        env_path = f"{bin_dir}:{bash_dir}:$PATH"

        self.run(f'PATH="{env_path}" "{bash}" "{self.source_folder}/test.sh"', env="conanrun")

        help_result = subprocess.run(
            [bash, prettyping, "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if help_result.returncode != 0:
            raise RuntimeError("prettyping --help failed")
        if "Usage:" not in help_result.stdout or "recentstats" not in help_result.stdout:
            raise RuntimeError("prettyping --help did not expose v1.1.0 options")

        mock_ping = os.path.join(self.source_folder, "mock-ping.sh")
        tool_dir = self.source_folder
        mock_env = dict(os.environ)
        mock_env["PATH"] = f"{tool_dir}{os.pathsep}{bash_dir}{os.pathsep}" + mock_env.get("PATH", "")
        run_result = subprocess.run(
            [
                bash,
                prettyping,
                "--nocolor",
                "--nounicode",
                "--noterminal",
                "--nolegend",
                "--last",
                "2",
                "--pingbin",
                mock_ping,
                "example.test",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            env=mock_env,
        )
        if run_result.returncode != 0:
            raise RuntimeError(f"prettyping mock run failed: {run_result.stderr}")
        if "lost;" not in run_result.stdout:
            raise RuntimeError("prettyping mock run did not print packet loss statistics")
        if "_" not in run_result.stdout:
            raise RuntimeError("prettyping mock run did not render ping samples")
