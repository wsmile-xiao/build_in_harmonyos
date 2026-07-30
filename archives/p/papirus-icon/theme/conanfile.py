#!/usr/bin/env python3
"""Conan recipe for papirus-icon/theme — pure icon theme resource package.

papirus-icon-theme is a free and open source SVG icon theme for Linux.
It is a pure resource/data package with no compilation step; "installation"
consists of copying the icon theme directories (Papirus, Papirus-Dark,
Papirus-Light) and license/authors files to share/icons/.

The upstream Makefile's `all:` target is intentionally empty; `install`
copies the icon theme directories to DESTDIR/share/icons/. The Conan recipe
reproduces this behavior: download, extract, copy resources, no build.

License: GPL-3.0-only
"""
import os
import tarfile
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, download, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class PapirusiconConan(ConanFile):
    name = "papirus-icon"
    version = "theme"
    description = "Papirus icon theme — free SVG icon theme for Linux"
    license = "GPL-3.0-only"
    homepage = "https://github.com/PapirusDevelopmentTeam/papirus-icon-theme"
    url = ""  # CI fills this

    settings = "os", "arch"

    package_type = "unknown"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        src = self.conan_data["sources"]
        archive_path = os.path.join(self.source_folder,
                                    "papirus-icon-theme-20250501.tar.gz")
        download(self, src["url"], archive_path,
                 sha256=src.get("sha256"))
        extract_to = os.path.join(self.source_folder, "_extracted")
        os.makedirs(extract_to, exist_ok=True)
        with tarfile.open(archive_path, "r:gz",
                          errorlevel=0) as tf:
            tf.extractall(path=extract_to, filter="data")
        items = os.listdir(extract_to)
        if len(items) == 1 and os.path.isdir(os.path.join(extract_to, items[0])):
            top = os.path.join(extract_to, items[0])
            for entry in os.listdir(top):
                os.rename(os.path.join(top, entry),
                          os.path.join(self.source_folder, entry))
        else:
            for entry in items:
                os.rename(os.path.join(extract_to, entry),
                          os.path.join(self.source_folder, entry))
        os.remove(archive_path)
        shutil.rmtree(extract_to, ignore_errors=True)

    def build(self):
        apply_conandata_patches(self)
        # No compilation step — upstream Makefile `all:` is intentionally empty.
        pass

    def package(self):
        for theme in ("Papirus", "Papirus-Dark", "Papirus-Light"):
            src = os.path.join(self.source_folder, theme)
            dst = os.path.join(self.package_folder, "share", "icons", theme)
            copy(self, "*", src=src, dst=dst, keep_path=True)

        for fn in ("LICENSE", "AUTHORS"):
            src = os.path.join(self.source_folder, fn)
            if os.path.isfile(src):
                copy(self, fn, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "share", "icons"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []

        icons_dir = os.path.join(self.package_folder, "share", "icons")
        self.buildenv_info.define("PAPIRUS_ICON_THEME_DIR", icons_dir)

        share_dir = os.path.join(self.package_folder, "share")
        existing_xdg = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
        self.buildenv_info.define("XDG_DATA_DIRS", f"{share_dir}:{existing_xdg}")

        self.output.info(f"PAPIRUS_ICON_THEME_DIR={icons_dir}")
