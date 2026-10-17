#!/usr/bin/env python3
"""Conan recipe for pipes-sh 1.3.0 — animated pipes terminal screensaver.

Upstream: https://github.com/pipeseroni/pipes.sh (v1.3.0, 2018-02)
Build: no compilation (pure Bash script — Makefile install copies pipes.sh to bin)
OHOS adaptation: chmod +x and copy script to bin/; no patches needed.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PipesShConan(ConanFile):
    name = "pipes-sh"
    version = "1.3.0"
    description = "Animated pipes terminal screensaver — Bash script"
    license = "MIT"
    homepage = "https://github.com/pipeseroni/pipes.sh"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def config_options(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pipes-sh only supports Linux/OHOS, got {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        script = os.path.join(self.source_folder, "pipes.sh")
        if os.path.isfile(script):
            os.chmod(script, 0o755)

    def package_id(self):
        self.info.clear()

    def package(self):
        copy(self, "pipes.sh", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        script = os.path.join(self.package_folder, "bin", "pipes.sh")
        if os.path.isfile(script):
            os.chmod(script, 0o755)
        copy(self, "pipes.sh.6", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man6"),
             keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
