#!/usr/bin/env python3
"""Conan recipe — prettyping 1.1.0.

prettyping is a pure Bash wrapper around ping. There is no compilation step;
packaging copies the executable script into bin/ and validates syntax/help.
"""
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PrettypingConan(ConanFile):
    name = "prettyping"
    version = "1.1.0"
    description = "A ping wrapper making output prettier, more colorful, compact, and easier to read"
    license = "MIT"
    homepage = "https://github.com/denilsonsa/prettyping"
    url = "https://github.com/denilsonsa/prettyping"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

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

    def build(self):
        apply_conandata_patches(self)
        script = os.path.join(self.source_folder, "prettyping")
        bash = self._bash()

        self.run(f'"{bash}" -n "{script}"')

        help_result = subprocess.run(
            [bash, script, "--help"],
            cwd=self.source_folder,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if help_result.returncode != 0:
            raise RuntimeError("prettyping --help returned a non-zero status")
        if "Usage:" not in help_result.stdout or "--pingbin" not in help_result.stdout:
            raise RuntimeError("prettyping --help did not contain expected usage text")

    def package(self):
        copy(self, "prettyping", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        script = os.path.join(self.package_folder, "bin", "prettyping")
        os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
