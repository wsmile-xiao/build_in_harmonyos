#!/usr/bin/env python3
"""Conan recipe — bashbro 1.13 (Bash-based web file browser).

Bashbro is a shell script that allows you to browse the filesystem,
view files and download them via a web browser. Runs a small HTTP
server in pure bash.

Pure bash script — no compilation. Install layout:
  bin/bashbro          — main script (#!/usr/bin/env bash)
  share/man/man1/bashbro.1  — man page

Run-time deps: bash. Optional: socat or netcat (port listener backends).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout


class BashbroConan(ConanFile):
    name = "bashbro"
    version = "1.13"
    description = "Bash-based web file browser (browse/stream/save via browser)"
    license = "GPL-3.0"
    homepage = "https://github.com/victrixsoft/bashbro"
    url = "https://github.com/victrixsoft/bashbro"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure bash script — nothing to compile.
        # Ensure the main script is executable.
        src = os.path.join(self.source_folder, "bashbro")
        if os.path.isfile(src):
            os.chmod(src, 0o755)

    def package(self):
        # Install main script to bin/
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "bashbro"),
            os.path.join(bin_dir, "bashbro"),
        )
        os.chmod(os.path.join(bin_dir, "bashbro"), 0o755)

        # Install man page to share/man/man1/
        man_dir = os.path.join(
            self.package_folder, "share", "man", "man1"
        )
        os.makedirs(man_dir, exist_ok=True)
        man_src = os.path.join(self.source_folder, "bashbro.1")
        if os.path.isfile(man_src):
            shutil.copy2(man_src, os.path.join(man_dir, "bashbro.1"))

        # Install LICENSE to share/bashbro/
        lic_dir = os.path.join(self.package_folder, "share", "bashbro")
        os.makedirs(lic_dir, exist_ok=True)
        lic_src = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(lic_src):
            shutil.copy2(lic_src, os.path.join(lic_dir, "LICENSE"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            self.buildenv_info.append_path("PATH", bin_dir)
