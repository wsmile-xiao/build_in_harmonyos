#!/usr/bin/env python3
"""Conan recipe — bundler-completion 1.0.3 (bash completion scripts, no compilation).

Ships the upstream "completion-bundle" script from mernen/completion-ruby:
command-line completion for the Ruby Bundler commands (bundle / bundler).
Pure text package — no binaries are built.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BundlerCompletionConan(ConanFile):
    name = "bundler-completion"
    version = "1.0.3"
    description = "Bash completion for the Ruby Bundler commands (bundle/bundler)"
    license = "MIT"
    homepage = "https://github.com/mernen/completion-ruby"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # No compilation needed — pure bash completion script

    def package(self):
        # bash-completion loads completions/<command> lazily, so the upstream
        # "completion-bundle" file is installed under the bundler command name
        # (same mapping as Homebrew's bundler-completion formula).
        completions = os.path.join(self.package_folder, "share", "bash-completion", "completions")
        copy(self, "completion-bundle", src=self.source_folder, dst=completions)
        os.rename(os.path.join(completions, "completion-bundle"),
                  os.path.join(completions, "bundler"))
        copy(self, "MIT-LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
