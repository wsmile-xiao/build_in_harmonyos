#!/usr/bin/env python3
"""Conan test_package for Zig 0.16.0."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class ZigTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["zig"]
        zig = os.path.join(dep.package_folder, "bin", "zig.exe" if str(self.settings.os) == "Windows" else "zig")
        self.run(f'"{zig}" version', env="conanrun")

        version = subprocess.run(
            [zig, "version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if version.returncode != 0:
            raise RuntimeError(version.stderr)
        if version.stdout.strip() != "0.16.0":
            raise RuntimeError(f"unexpected Zig version: {version.stdout!r}")

        project_dir = os.path.join(self.build_folder, "smoke")
        os.makedirs(project_dir, exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "build.zig"), os.path.join(project_dir, "build.zig"))
        shutil.copy2(os.path.join(self.source_folder, "smoke.zig"), os.path.join(project_dir, "smoke.zig"))

        if str(self.settings.os) != "Windows":
            script = os.path.join(self.source_folder, "test.sh")
            self.run(f'sh "{script}" "{zig}" "{project_dir}"', env="conanrun")
            return

        self.run(f'"{zig}" build run install --summary all -Doptimize=ReleaseSmall', cwd=project_dir, env="conanrun")
        exe = os.path.join(project_dir, "smoke.exe" if str(self.settings.os) == "Windows" else "smoke")
        installed_exe = os.path.join(project_dir, "zig-out", "bin", os.path.basename(exe))
        if not os.path.exists(installed_exe):
            raise RuntimeError("Zig did not produce the smoke executable")

        run_result = subprocess.run(
            [installed_exe],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if run_result.returncode != 0:
            raise RuntimeError(run_result.stderr)
