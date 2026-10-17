#!/usr/bin/env python3
"""Conan recipe — bruno-cli 3.4.2 (npm).

Packages the Bruno CLI (bru) — a command-line tool for running
API collections defined in the Bruno format.
"""

import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class BrunoCliConan(ConanFile):
    name = "bruno-cli"
    version = "3.4.2"
    description = "Command-line tool for running Bruno API collections"
    license = "MIT"
    homepage = "https://github.com/usebruno/bruno"
    url = ""

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is only supported on Linux/OHOS, "
                f"not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run(
            "npm install --ignore-scripts --no-audit --no-fund "
            "--no-package-lock --no-save",
            cwd=self.source_folder,
        )

    def package(self):
        app_dir = os.path.join(self.package_folder, "res", "bruno-cli")
        for directory in ("bin", "src"):
            copy(
                self,
                "*",
                src=os.path.join(self.source_folder, directory),
                dst=os.path.join(app_dir, directory),
                keep_path=True,
            )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "node_modules"),
            dst=os.path.join(app_dir, "node_modules"),
            keep_path=True,
        )
        for filename in ("package.json", "license.md", "changelog.md", "readme.md"):
            copy(
                self,
                filename,
                src=self.source_folder,
                dst=app_dir,
                keep_path=False,
            )
        copy(
            self,
            "license.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        launcher = os.path.join(self.package_folder, "bin", "bru")
        save(
            self,
            launcher,
            "#!/bin/sh\n"
            "set -eu\n"
            "script_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
            "exec node --jitless "
            "\"$script_dir/../res/bruno-cli/bin/bru.js\" \"$@\"\n",
        )
        try:
            os.chmod(
                launcher,
                os.stat(launcher).st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )
        except OSError:
            # HMDFS/SELinux: chmod may be a silent no-op (E046); the launcher
            # is also reachable via `sh <path>` so a missing +x is non-fatal.
            pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
