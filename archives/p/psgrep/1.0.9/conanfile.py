#!/usr/bin/env python3
"""Conan recipe — psgrep 1.0.9

psgrep is a pure Bash script that wraps ps + grep for process-list search.
There is no compilation step; packaging copies the executable script and man page.
"""
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PsgrepConan(ConanFile):
    name = "psgrep"
    version = "1.0.9"
    description = "Shortcut shell utility for searching the process list with grep"
    license = "GPL-3.0-or-later"
    homepage = "https://jvz.github.io/psgrep/"
    url = "https://github.com/jvz/psgrep"

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _bash(self):
        for candidate in (os.environ.get("CONFIG_SHELL"), shutil.which("bash"), "/data/service/hnp/bin/bash", os.environ.get("SHELL")):
            if candidate and os.path.exists(candidate):
                return candidate
        return "bash"

    def build(self):
        apply_conandata_patches(self)

        psgrep = os.path.join(self.source_folder, "psgrep")
        install_sh = os.path.join(self.source_folder, "install.sh")

        # Upstream has no dedicated test suite. Validate shell syntax and the
        # installer's argument handling before packaging.
        bash = self._bash()
        self.run(f'"{bash}" -n "{psgrep}"')
        self.run(f'"{bash}" -n "{install_sh}"')

        result = subprocess.run(
            [bash, install_sh, "--help"],
            cwd=self.source_folder,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 1 or "Usage:" not in result.stdout:
            raise RuntimeError("install.sh usage check failed")

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "psgrep", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(
            self,
            "psgrep.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )

        psgrep_path = os.path.join(self.package_folder, "bin", "psgrep")
        os.chmod(psgrep_path, os.stat(psgrep_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
