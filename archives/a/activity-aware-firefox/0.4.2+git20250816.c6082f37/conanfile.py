#!/usr/bin/env python3
"""Conan recipe — activity-aware-firefox 0.4.2 (script package)."""

import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
)
from conan.tools.layout import basic_layout


class ActivityAwareFirefoxConan(ConanFile):
    name = "activity-aware-firefox"
    version = "0.4.2+git20250816.c6082f37"
    description = "Firefox profile wrapper with pluggable desktop activity context"
    license = "MIT-0"
    homepage = "https://gitlab.com/hook/activity-aware-firefox"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Windows"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS for script packaging: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        script = os.path.join(self.source_folder, "activityfirefox")
        content = load(self, script)
        required_markers = (
            "--activity-id",
            "--activity-name",
            "--probe-context",
            "ACTIVITY_PROVIDER",
        )
        missing = [marker for marker in required_markers if marker not in content]
        if missing:
            raise ConanInvalidConfiguration(
                "Portable activity context patch is incomplete: " + ", ".join(missing)
            )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "activityfirefox", src=self.source_folder, dst=bindir)
        copy(
            self,
            "activityfirefox.desktop",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "applications"),
        )
        copy(
            self,
            "MIT-0.txt",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        script = os.path.join(bindir, "activityfirefox")
        os.chmod(
            script,
            os.stat(script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
