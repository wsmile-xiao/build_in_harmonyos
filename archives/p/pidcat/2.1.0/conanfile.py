#!/usr/bin/env python3
"""Conan recipe — pidcat: colored adb logcat script for Android development.

pidcat is a Python script that wraps adb logcat with colorized output,
filtering by application package name. It is a pure Python tool (no C/C++).
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PidcatConan(ConanFile):
    name = "pidcat"
    version = "2.1.0"
    description = "Colored logcat script which only shows log entries for a specific application package"
    license = "Apache-2.0"
    homepage = "https://github.com/JakeWharton/pidcat"
    url = ""

    package_type = "application"

    # Pure Python script — no C/C++ compiler settings needed

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # pidcat is a pure Python script — no compilation needed.
        # The shebang is already patched in 0001-pidcat.py.patch.
        pass

    def package(self):
        # Install pidcat.py as bin/pidcat
        copy(self, "pidcat.py", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Rename to pidcat (drop .py extension) for cleaner CLI usage
        src = os.path.join(self.package_folder, "bin", "pidcat.py")
        dst = os.path.join(self.package_folder, "bin", "pidcat")
        if os.path.exists(src) and not os.path.exists(dst):
            os.rename(src, dst)
        # Shell completions (optional)
        copy(self, "bash_completion.d/*", self.source_folder, os.path.join(self.package_folder, "share", "bash-completion", "completions"))
        copy(self, "zsh-completion/*", self.source_folder, os.path.join(self.package_folder, "share", "zsh", "site-functions"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # No libs — this is a script-only package
