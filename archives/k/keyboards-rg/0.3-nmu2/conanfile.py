#!/usr/bin/env python3
"""Conan recipe for the Debian-native keyboards-rg data package."""

from __future__ import annotations

import json
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KeyboardsRgConan(ConanFile):
    name = "keyboards-rg"
    version = "0.3-nmu2"
    description = "Various XKB and Linux console keyboard layouts"
    license = "GPL-2.0-or-later OR X11"
    homepage = "https://packages.debian.org/sid/keyboards-rg"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"

    settings = "os", "arch", "compiler", "build_type"

    _source_files = {
        "layouts-xkb/eo_rg",
        "layouts-xkb/pancyr",
        "layouts-xkb/sk_rg",
        "layouts-xkb/sk_snk",
        "layouts-console/ru_rg.kmap",
        "layouts-console/sk_rg.kmap",
        "scripts/cyrx",
        "scripts/eox",
        "scripts/skx",
        "COPYING",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"keyboards-rg supports Linux and OHOS, not {self.settings.os}"
            )

    def package_id(self):
        # The package contains target-independent keyboard data and shell text.
        self.info.clear()

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][str(self.version)])
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def _source_path(self, relative: str) -> Path:
        return Path(self.source_folder).joinpath(*relative.split("/"))

    def build(self):
        missing = [relative for relative in sorted(self._source_files) if not self._source_path(relative).is_file()]
        if missing:
            raise ConanException(f"keyboards-rg source payload is incomplete: {missing}")

        empty = [
            relative
            for relative in sorted(self._source_files)
            if self._source_path(relative).stat().st_size == 0
        ]
        if empty:
            raise ConanException(f"keyboards-rg source payload contains empty files: {empty}")

        forbidden_suffixes = {".a", ".dll", ".dylib", ".o", ".obj", ".so"}
        generated = [
            path.relative_to(self.source_folder).as_posix()
            for path in Path(self.source_folder).rglob("*")
            if path.is_file() and path.suffix.lower() in forbidden_suffixes
        ]
        if generated:
            raise ConanException(f"unexpected generated binary in source tree: {generated}")

        marker = {
            "status": "not_available",
            "framework": "Debian source package",
            "command": "none",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, separators=(",", ":")))

    def package(self):
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "layouts-xkb"),
            dst=os.path.join(self.package_folder, "share", "X11", "xkb", "symbols"),
            keep_path=False,
        )
        copy(
            self,
            "*.kmap",
            src=os.path.join(self.source_folder, "layouts-console"),
            dst=os.path.join(self.package_folder, "share", "keymaps", "i386", "qwerty"),
            keep_path=False,
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "scripts"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        expected = {
            Path(self.package_folder) / "share" / "X11" / "xkb" / "symbols": 4,
            Path(self.package_folder) / "share" / "keymaps" / "i386" / "qwerty": 2,
            Path(self.package_folder) / "bin": 3,
        }
        for directory, minimum in expected.items():
            files = [path for path in directory.glob("*") if path.is_file()]
            if len(files) != minimum:
                raise ConanException(
                    f"installed keyboards-rg inventory mismatch in {directory}: "
                    f"{len(files)} != {minimum}"
                )

        license_file = Path(self.package_folder) / "licenses" / "COPYING"
        if not license_file.is_file() or license_file.stat().st_size == 0:
            raise ConanException("keyboards-rg COPYING was not packaged")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]

        xkb_dir = os.path.join(self.package_folder, "share", "X11", "xkb")
        console_dir = os.path.join(
            self.package_folder, "share", "keymaps", "i386", "qwerty"
        )
        self.buildenv_info.define_path("KEYBOARDS_RG_XKB_DATA_DIR", xkb_dir)
        self.runenv_info.define_path("KEYBOARDS_RG_XKB_DATA_DIR", xkb_dir)
        self.buildenv_info.define_path("KEYBOARDS_RG_CONSOLE_MAP_DIR", console_dir)
        self.runenv_info.define_path("KEYBOARDS_RG_CONSOLE_MAP_DIR", console_dir)
