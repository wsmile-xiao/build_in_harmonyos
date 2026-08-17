#!/usr/bin/env python3
"""Conan recipe — bash-completion 2.17.0 (shell script package).

bash-completion is a collection of shell command completions for the Bash shell.
It installs shell scripts to share/bash-completion/ — no compiled binaries.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BashCompletionConan(ConanFile):
    name = "bash-completion"
    version = "2.17.0"
    description = "Programmable completion functions for bash"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/scop/bash-completion"
    url = "https://github.com/scop/bash-completion"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix: HarmonyOS HMDFS rejects file creation in dirs created with
        # `umask 077 && mktemp -d` (setgid + no group execute = Permission denied).
        # Patch configure template so generated config.status works on HarmonyOS.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            replace_in_file(self, configure_path,
                            "umask 077 && mktemp -d", "mktemp -d")
            replace_in_file(self, configure_path,
                            "umask 077 && mkdir", "mkdir")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
