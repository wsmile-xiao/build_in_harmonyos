#!/usr/bin/env python3
"""Conan recipe for the X Keyboard Configuration data package."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class XKeyboardConfigConan(ConanFile):
    name = "xkeyboard-config"
    version = "2.48"
    description = "X Keyboard Configuration data, rules, and symbols"
    license = "MIT"
    homepage = "https://www.x.org/wiki/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xkeyboard-config supports Linux and OHOS, not {self.settings.os}"
            )

    def package_id(self):
        # The installed data and generated rules are target-independent.
        self.info.clear()

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][str(self.version)])
        local_archive = os.getenv("XKEYBOARD_CONFIG_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve()
            if not archive.is_file():
                raise ConanException(f"source archive is not a regular file: {archive}")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        toolchain = MesonToolchain(self)
        nls_enabled = os.getenv("XKEYBOARD_CONFIG_NLS", "true").lower() not in (
            "0",
            "false",
            "off",
        )
        toolchain.project_options.update(
            {
                "compat-rules": True,
                "xorg-rules-symlinks": False,
                "nls": nls_enabled,
                "non-latin-layouts-list": False,
            }
        )
        toolchain.generate()

    @staticmethod
    def _format_command(command):
        if os.name == "nt":
            return subprocess.list2cmdline(command)
        return shlex.join(command)

    def _setup_meson(self):
        command = ["meson", "setup", self.build_folder, self.source_folder]
        if cross_building(self):
            cross_file = Path(self.generators_folder) / "conan_meson_cross.ini"
            if not cross_file.is_file():
                raise ConanException(f"Meson cross file is missing: {cross_file}")
            command += ["--cross-file", str(cross_file)]

        # Conan on Windows can otherwise turn the POSIX target prefix into F:/.
        command += ["--prefix=/", "--wrap-mode=nofallback"]
        self.run(self._format_command(command))

    def build(self):
        self._setup_meson()
        Meson(self).build()
        if can_run(self) and not cross_building(self):
            self.run(
                self._format_command(
                    [
                        "meson",
                        "test",
                        "-C",
                        self.build_folder,
                        "--no-rebuild",
                        "--print-errorlogs",
                        "--num-processes",
                        "1",
                    ]
                )
            )

    def package(self):
        Meson(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        root = Path(self.package_folder) / "share" / "xkeyboard-config-2"
        if not root.is_dir():
            raise ConanException(f"installed XKB root is missing: {root}")
        minimum_counts = {
            "compat": 22,
            "geometry": 30,
            "keycodes": 21,
            # meson.build is a source-side build description excluded by
            # symbols/meson.build's install_subdir() rule.
            "symbols": 197,
            # The upstream install rule excludes the optional custom types
            # directory from the packaged data set.
            "types": 12,
        }
        for name, minimum in minimum_counts.items():
            directory = root / name
            files = [
                path
                for path in directory.rglob("*")
                if path.is_file() and not path.is_symlink()
            ]
            if len(files) < minimum:
                raise ConanException(
                    f"installed {name} inventory is incomplete: {len(files)} < {minimum}"
                )

        for name in (
            "base",
            "evdev",
            "base.lst",
            "evdev.lst",
            "base.xml",
            "evdev.xml",
            "base.extras.xml",
            "evdev.extras.xml",
            "xkb.dtd",
        ):
            path = root / "rules" / name
            if not path.is_file() or path.stat().st_size == 0:
                raise ConanException(
                    f"generated rules artifact is missing or empty: {path}"
                )

        pc_dir = Path(self.package_folder) / "share" / "pkgconfig"
        pc_dir.mkdir(parents=True, exist_ok=True)
        pc_path = pc_dir / "xkeyboard-config-2.pc"
        if not pc_path.is_file():
            raise ConanException(f"pkg-config metadata is missing: {pc_path}")
        pc_path.write_text(
            "prefix=${pcfiledir}/../..\n"
            "exec_prefix=${prefix}\n"
            "datarootdir=${prefix}/share\n"
            "datadir=${datarootdir}\n"
            "xkb_root=${datadir}/xkeyboard-config-2\n"
            "xkb_base=${datadir}/X11/xkb\n\n"
            "Name: XKeyboardConfig\n"
            "Description: X Keyboard Configuration data\n"
            f"Version: {self.version}\n",
            encoding="utf-8",
            newline="\n",
        )

        aliases = {
            Path(self.package_folder) / "share" / "X11" / "xkb": "/share/xkeyboard-config-2",
            pc_dir / "xkeyboard-config.pc": "xkeyboard-config-2.pc",
        }
        for required, expected_target in aliases.items():
            if required.is_symlink():
                target = os.readlink(required)
                if target != expected_target:
                    raise ConanException(
                        f"compatibility alias target mismatch: {required} -> {target!r}"
                    )
            elif not required.exists():
                raise ConanException(f"compatibility alias is missing: {required}")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.set_property("pkg_config_name", "xkeyboard-config-2")
        pc_dir = os.path.join(self.package_folder, "share", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
