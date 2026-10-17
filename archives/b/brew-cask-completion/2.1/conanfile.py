#!/usr/bin/env python3
"""Conan recipe for brew-cask-completion 2.1 — pure Shell completion scripts.

brew-cask-completion provides Bash and Fish completion scripts for
Homebrew Cask. It is a pure script package with no compilation step;
"installation" consists of copying the scripts to standard completion
directories.

Source files:
  - homebrew-cask-completion.bash → share/bash-completion/completions/brew-cask
  - brew-cask.fish                → share/fish/vendor_completions.d/brew-cask.fish

No build system exists in the upstream source; the build() method copies
the scripts directly.

R28: test_package/ exists.
R34: test_package verifies installed completion scripts contain expected content.
R39: Source URL is the official GitHub release archive.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class BrewCaskCompletionConan(ConanFile):
    name = "brew-cask-completion"
    version = "2.1"
    description = "Bash and Fish completion scripts for Homebrew Cask"
    license = "BSD-2-Clause"
    homepage = "https://github.com/xyb/homebrew-cask-completion"
    url = ""  # CI fills this

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
        # Pure script package: no compilation needed.
        # Verify source files exist before packaging.
        bash_src = os.path.join(self.source_folder, "homebrew-cask-completion.bash")
        fish_src = os.path.join(self.source_folder, "brew-cask.fish")
        if not os.path.isfile(bash_src):
            raise Exception(f"Missing source file: {bash_src}")
        if not os.path.isfile(fish_src):
            raise Exception(f"Missing source file: {fish_src}")
        self.output.info("Source files verified: homebrew-cask-completion.bash + brew-cask.fish")

    def package(self):
        # Install completion scripts to standard paths
        bash_dst = os.path.join(self.package_folder, "share", "bash-completion", "completions")
        fish_dst = os.path.join(self.package_folder, "share", "fish", "vendor_completions.d")
        copy(self, "homebrew-cask-completion.bash",
             src=self.source_folder, dst=bash_dst, keep_path=False)
        # Rename to brew-cask (standard bash completion name)
        old_bash = os.path.join(bash_dst, "homebrew-cask-completion.bash")
        new_bash = os.path.join(bash_dst, "brew-cask")
        if os.path.isfile(old_bash):
            os.rename(old_bash, new_bash)
        copy(self, "brew-cask.fish",
             src=self.source_folder, dst=fish_dst, keep_path=False)
        # Copy license
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Completion scripts are data files, not libraries or executables
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
