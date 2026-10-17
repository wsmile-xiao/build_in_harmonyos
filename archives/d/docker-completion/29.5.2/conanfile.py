#!/usr/bin/env python3
"""Conan recipe — docker-completion 29.5.2 (bash completion script, no compilation)."""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class DockerCompletionConan(ConanFile):
    name = "docker-completion"
    version = "29.5.2"
    description = "Docker CLI bash completion script"
    license = "Apache-2.0"
    homepage = "https://github.com/docker/cli"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # No compilation needed - pure bash completion script

    def package(self):
        copy(self, "docker",
             src=os.path.join(self.source_folder, "contrib", "completion", "bash"),
             dst=os.path.join(self.package_folder, "share", "bash-completion", "completions"))

    def package_info(self):
        self.cpp_info.resdirs = ["share"]
