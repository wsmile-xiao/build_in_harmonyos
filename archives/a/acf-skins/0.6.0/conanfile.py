#!/usr/bin/env python3
"""Conan recipe for the ACF web-interface skins 0.6.0."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcfSkinsConan(ConanFile):
    name = "acf-skins"
    version = "0.6.0"
    description = "Web-interface skins for the Alpine Configuration Framework"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-skins"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch"

    _resource_dir = os.path.join("share", "acf", "www", "skins")
    _theme_dirs = ("alps", "clouds", "ice", "snow", "wik")
    _static_files = (
        ("static", "reset.css"),
        ("static/tango/16x16/categories", "applications-internet.png"),
        ("static/tango/16x16/categories", "applications-system.png"),
        ("static/tango/16x16/places", "start-here.png"),
        ("static/tango/16x16/places", "network-server.png"),
        ("static/tango/16x16/status", "network*.png"),
        ("static/tango/16x16/devices", "computer.png"),
        ("static/tango/16x16/devices", "network*.png"),
        ("static/tango/16x16/apps", "system-users.png"),
        ("static/tango/16x16/apps", "utilities*.png"),
        ("static/tango/16x16/emblems", "emblem-unreadable.png"),
        ("static/tango/16x16/actions", "list*.png"),
        ("static/tango/16x16/actions", "go*.png"),
        ("static/tango/16x16/actions", "document-properties.png"),
    )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="acf-skins-v0.6.0.tar.gz",
            strip_root=True,
        )

    def build(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-skins does not support os={self.settings.os}"
            )

        root = Path(self.source_folder)
        selected = set()
        for directory in self._theme_dirs:
            selected.update(path for path in (root / directory).rglob("*") if path.is_file())
        for directory, pattern in self._static_files:
            selected.update(path for path in (root / directory).glob(pattern) if path.is_file())

        suffix_counts = {
            suffix: sum(path.suffix.lower() == suffix for path in selected)
            for suffix in (".css", ".js", ".png", ".jpg")
        }
        expected = {".css": 7, ".js": 5, ".png": 62, ".jpg": 7}
        if len(selected) != 81 or suffix_counts != expected:
            raise ConanInvalidConfiguration(
                "Unexpected ACF skins inventory: expected 81 files "
                f"({expected}), found {len(selected)} ({suffix_counts})"
            )

    def package(self):
        destination = os.path.join(self.package_folder, self._resource_dir)
        for directory in self._theme_dirs:
            copy(
                self,
                "*",
                src=os.path.join(self.source_folder, directory),
                dst=os.path.join(destination, directory),
            )
        for directory, pattern in self._static_files:
            copy(
                self,
                pattern,
                src=os.path.join(self.source_folder, *directory.split("/")),
                dst=os.path.join(destination, *directory.split("/")),
                keep_path=False,
            )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = [self._resource_dir]
        resource_root = os.path.join(self.package_folder, self._resource_dir)
        self.buildenv_info.define_path("ACF_SKINS_ROOT", resource_root)
        self.runenv_info.define_path("ACF_SKINS_ROOT", resource_root)
