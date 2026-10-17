"""Unmodified KDE Breeze GRUB theme resources, relocatable on HarmonyOS."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class BreezeGrubConan(ConanFile):
    name = "breeze-grub"
    version = "6.7.2"
    package_type = "unknown"
    license = ("GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL", "CC0-1.0",
               "CC-BY-SA-4.0", "GPL-2.0-or-later WITH Font-exception-2.0", "BSD-2-Clause")
    homepage = "https://invent.kde.org/plasma/breeze-grub"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = "Breeze theme assets for GRUB, packaged as relocatable resources"
    topics = ("grub", "breeze", "theme", "resources", "ohos")
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # KDE ships final PNG/PF2 assets; mkfont.sh is an optional authoring tool.
        # The upstream archive has no make/CTest/pytest functional test suite.
        theme = os.path.join(self.source_folder, "breeze")
        if len(os.listdir(theme)) != 23 or not os.path.isfile(os.path.join(theme, "theme.txt")):
            raise ConanException("Incomplete upstream Breeze resource tree")
        self.output.info("Validated upstream resource tree; no compilation is required")

    def package(self):
        copy(self, "*", src=os.path.join(self.source_folder, "breeze"),
             dst=os.path.join(self.package_folder, "share", "grub", "themes", "breeze"))
        copy(self, "*", src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "REUSE.toml", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = [os.path.join("share", "grub", "themes", "breeze")]
        self.runenv_info.define_path("BREEZE_GRUB_THEME_DIR", os.path.join(
            self.package_folder, "share", "grub", "themes", "breeze"))
