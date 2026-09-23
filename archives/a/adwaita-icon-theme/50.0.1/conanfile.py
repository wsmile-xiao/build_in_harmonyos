#!/usr/bin/env python3
"""Conan recipe — adwaita-icon-theme 50.0.1 (data-only icon theme, Meson).

Data-only package: no libraries, no executables, no headers.
Installs icon theme data (Adwaita/) + index.theme + licenses +
a dataonly pkg-config file (adwaita-icon-theme.pc).

Adaptation notes (OHOS):
- gtk4-update-icon-cache / gtk-update-icon-cache is not available on the
  OHOS build host; patch 0001 makes it optional (configure + install
  succeed without it; the cache script is skipped when not found).
- patch 0002 installs the dataonly .pc into libdir/pkgconfig so the
  package carries a lib/ artifact (G4 gate) and pkg-config consumers
  can locate it via PKG_CONFIG_PATH.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class AdwaitaIconThemeConan(ConanFile):
    win_bash = True
    name = "adwaita-icon-theme"
    version = "50.0.1"
    description = "A collection of icons used as the basis for GNOME themes"
    license = "LGPL-3.0-or-later OR CC-BY-SA-3.0-US"
    homepage = "https://gitlab.gnome.org/GNOME/adwaita-icon-theme"
    url = ""  # CI fills this

    # Keep package_type neutral: this is a data-only package, not a CLI tool.
    package_type = "unknown"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        # OHOS 适配版 conan 的 Meson 助手使用 build()（等价 meson compile）
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # Meson keeps selected icon/cursor aliases as symlinks upstream. On
        # OHOS/HMDFS or Windows destdir installs these links can be skipped, so
        # materialize the public aliases as ordinary files when missing.
        icon_root = os.path.join(self.package_folder, "share", "icons", "Adwaita")

        def copy_alias(src, dst):
            if os.path.isfile(src) and not os.path.lexists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)

        src_cursors = os.path.join(self.source_folder, "Adwaita", "cursors")
        dst_cursors = os.path.join(icon_root, "cursors")
        if os.path.isdir(src_cursors):
            os.makedirs(dst_cursors, exist_ok=True)
            for name in os.listdir(src_cursors):
                if "." in name:
                    continue
                copy_alias(os.path.join(src_cursors, name), os.path.join(dst_cursors, name))

            cursor_aliases = {
                "default": ("left_ptr",),
                "pointer": ("hand2",),
                "text": ("xterm",),
                "wait": ("watch",),
            }
            for source_name, aliases in cursor_aliases.items():
                packaged_source = os.path.join(dst_cursors, source_name)
                upstream_source = os.path.join(src_cursors, source_name)
                source = packaged_source if os.path.isfile(packaged_source) else upstream_source
                for alias in aliases:
                    copy_alias(source, os.path.join(dst_cursors, alias))

        copy_alias(
            os.path.join(icon_root, "scalable", "places", "folder.svg"),
            os.path.join(icon_root, "scalable", "status", "folder-open.svg"),
        )

    def package_info(self):
        # Data-only package: expose the dataonly pkg-config file for consumers.
        self.cpp_info.set_property("pkg_config_name", "adwaita-icon-theme")
        # No libraries / headers / binaries to declare.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
