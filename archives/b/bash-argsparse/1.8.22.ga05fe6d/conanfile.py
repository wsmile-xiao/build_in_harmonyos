#!/usr/bin/env python3
"""Conan recipe for bash-argsparse 1.8.22.ga05fe6d."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class BashArgsparseConan(ConanFile):
    name = "bash-argsparse"
    version = "1.8.22.ga05fe6d"
    description = "High-level command-line argument parsing library for GNU Bash"
    license = "WTFPL"
    homepage = "https://github.com/Anvil/bash-argsparse"
    url = "https://github.com/Anvil/bash-argsparse"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bash/5.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Run the complete upstream suite with the packaged Bash. On HarmonyOS
        # the patched library automatically uses its internal getopt fallback.
        bash = os.path.join(self.dependencies["bash"].package_folder, "bin", "bash")
        self.run(f'"{bash}" ./unittest', cwd=self.source_folder)

    def package(self):
        share_dir = os.path.join(self.package_folder, "share", "bash-argsparse")
        copy(self, "argsparse.sh", src=self.source_folder, dst=share_dir)
        copy(self, "argsparse-completion.sh", src=self.source_folder, dst=share_dir)
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "tutorial"),
            dst=os.path.join(share_dir, "tutorial"),
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "bash-argsparse"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        share_dir = os.path.join(self.package_folder, "share", "bash-argsparse")
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.define("BASH_ARGSPARSE_ROOT", share_dir)
        self.buildenv_info.define("BASH_ARGSPARSE_ROOT", share_dir)
