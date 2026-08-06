#!/usr/bin/env python3
"""Conan recipe — adwaita-icon-theme 50.0 (data-only icon theme, Meson).

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
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class AdwaitaIconThemeConan(ConanFile):
    name = "adwaita-icon-theme"
    version = "50.0"
    description = "A collection of icons used as the basis for GNOME themes"
    license = "LGPL-3.0-or-later OR CC-BY-SA-3.0-US"
    homepage = "https://gitlab.gnome.org/GNOME/adwaita-icon-theme"
    url = ""  # CI fills this

    package_type = "application"

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

    def package_info(self):
        # Data-only package: expose the dataonly pkg-config file for consumers.
        self.cpp_info.set_property("pkg_config_name", "adwaita-icon-theme")
        # No libraries / headers / binaries to declare.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
