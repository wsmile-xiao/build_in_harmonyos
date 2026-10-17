#!/usr/bin/env python3
"""Conan recipe for the islamic-menus XDG desktop data package."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class IslamicMenusConan(ConanFile):
    name = "islamic-menus"
    version = "1.0.5"
    package_type = "build-scripts"
    license = "GPL-3.0-or-later"
    homepage = "https://launchpad.net/islamic-menus"
    description = "XDG menu categories and icons for Islamic applications"

    # Keep the standard OHOS profile settings for Conan CI and package identity.
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"islamic-menus supports Linux and OHOS XDG desktops, not {self.settings.os}"
            )

    def build_requirements(self):
        # The upstream Makefile uses intltool-merge to materialize localized
        # .directory files from the shipped .po catalogs.
        self.tool_requires("intltool/0.51.0")

    def export_sources(self):
        # Keep the standard Conan patch-export hook; this release has no patches.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Empty patches mapping; this is a no-op for upstream 1.0.5.
        apply_conandata_patches(self)
        po_dir = os.path.join(self.source_folder, "po")
        output_dir = os.path.join(self.build_folder, "desktop-directories")
        os.makedirs(output_dir, exist_ok=True)

        for template in ("Islamic-Software.directory.in", "Quran.directory.in"):
            source = os.path.join(self.source_folder, template)
            output = os.path.join(output_dir, template[:-3])
            self.run(
                f'intltool-merge -d "{po_dir}" "{source}" "{output}"',
                env="conanbuild",
            )

    def package(self):
        xdg_menu_dirs = (
            "applications-merged",
            "applications-gnome-merged",
        )
        for menu_dir in xdg_menu_dirs:
            destination = os.path.join(
                self.package_folder, "etc", "xdg", "menus", menu_dir
            )
            copy(
                self,
                "islamic.menu",
                src=self.source_folder,
                dst=destination,
            )

        directories_dst = os.path.join(
            self.package_folder, "share", "desktop-directories"
        )
        copy(
            self,
            "*.directory",
            src=os.path.join(self.build_folder, "desktop-directories"),
            dst=directories_dst,
        )

        icons_dst = os.path.join(
            self.package_folder,
            "share",
            "icons",
            "hicolor",
            "scalable",
            "categories",
        )
        copy(
            self,
            "*.svg",
            src=os.path.join(self.source_folder, "icons"),
            dst=icons_dst,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Let XDG-aware consumers discover the package when Conan's runtime
        # environment is activated.
        self.runenv_info.append_path(
            "XDG_CONFIG_DIRS", os.path.join(self.package_folder, "etc", "xdg")
        )
        self.runenv_info.append_path(
            "XDG_DATA_DIRS", os.path.join(self.package_folder, "share")
        )
