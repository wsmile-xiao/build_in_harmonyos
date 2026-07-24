#!/usr/bin/env python3
"""Conan recipe — gws (bash script tool for git workspace management).

gws is a KISS, bash, colorful helper to manage workspaces composed of Git
repositories. It is a pure bash script with no compilation needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, chdir, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GwsConan(ConanFile):
    name = "gws"
    version = "0.2.0"
    description = "Manage workspaces composed of git repositories"
    license = "MIT"
    homepage = "https://streakycobra.github.io/gws/"
    url = ""  # CI fills this

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

    def build(self):
        apply_conandata_patches(self)
        # Pure bash script — no compilation needed
        pass

    def package(self):
        # In Conan 2, source files are in the source_folder during package()
        import shutil
        src_dir = self.source_folder
        pkg_dir = self.package_folder

        # Install main script
        os.makedirs(os.path.join(pkg_dir, "bin"), exist_ok=True)
        shutil.copy2(os.path.join(src_dir, "src", "gws"),
                     os.path.join(pkg_dir, "bin", "gws"))
        os.chmod(os.path.join(pkg_dir, "bin", "gws"), 0o755)

        # Install completions
        os.makedirs(os.path.join(pkg_dir, "etc", "bash_completion.d"), exist_ok=True)
        shutil.copy2(os.path.join(src_dir, "completions", "bash"),
                     os.path.join(pkg_dir, "etc", "bash_completion.d", "gws"))
        os.makedirs(os.path.join(pkg_dir, "usr", "share", "zsh", "vendor-completions"), exist_ok=True)
        shutil.copy2(os.path.join(src_dir, "completions", "zsh"),
                     os.path.join(pkg_dir, "usr", "share", "zsh", "vendor-completions", "_gws"))

        # Install documentation
        os.makedirs(os.path.join(pkg_dir, "share", "doc", "gws"), exist_ok=True)
        for f in ["LICENSE", "CHANGELOG", "README.md"]:
            shutil.copy2(os.path.join(src_dir, f),
                         os.path.join(pkg_dir, "share", "doc", "gws", f))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
