#!/usr/bin/env python3
"""Conan test package for zinit 3.15.0 — verify zinit scripts are installed and usable."""
import os
import shlex
import shutil
import subprocess

from conan import ConanFile


class ZinitTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        zinit_dir = os.path.join(self.dependencies["zinit"].package_folder, "share", "zinit")
        package_folder = shlex.quote(self.dependencies["zinit"].package_folder)
        self.run(f"CONAN_PACKAGE_FOLDER_zinit={package_folder} sh test.sh")

        for script in ["zinit.zsh", "zinit-autoload.zsh", "zinit-install.zsh"]:
            script_path = shlex.quote(os.path.join(zinit_dir, script))
            self.run(f"test -f {script_path}", cwd=zinit_dir)
        version_path = shlex.quote(os.path.join(zinit_dir, "VERSION"))
        zinit_script = shlex.quote(os.path.join(zinit_dir, "zinit.zsh"))
        self.run(f"grep -q '3.15.0' {version_path}", cwd=zinit_dir)
        self.run(f"test -x {zinit_script}", cwd=zinit_dir)

        zsh = shutil.which("zsh")
        if zsh:
            for script in ["zinit.zsh", "zinit-autoload.zsh", "zinit-install.zsh"]:
                spath = os.path.join(zinit_dir, script)
                rc = subprocess.run([zsh, "-n", spath], capture_output=True, timeout=30).returncode
                assert rc == 0, f"zsh syntax check failed for {script}"
            zinit_script = os.path.join(zinit_dir, "zinit.zsh")
            rc = subprocess.run(
                [zsh, "-fc", f"source {zinit_script!r}; typeset -f zinit >/dev/null"],
                capture_output=True,
                timeout=30,
            ).returncode
            assert rc == 0, "zinit.zsh did not define zinit function after source"
            self.output.info("zinit source/function check passed")
        else:
            self.run(f"grep -q '^[[:space:]]*zinit()' {zinit_script}", cwd=zinit_dir)
            self.output.info("zsh not available, validated zinit function definition text")

        self.output.info("zinit 3.15.0 test_package: all checks passed")
