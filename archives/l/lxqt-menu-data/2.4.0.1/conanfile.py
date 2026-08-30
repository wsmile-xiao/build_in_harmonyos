#!/usr/bin/env python3
"""Conan recipe — lxqt-menu-data 2.4.0.

lxqt-menu-data is a pure data package: XDG menu definitions
(.menu files), desktop-directories, and translations. No C/C++
code is compiled — the package just installs data files.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class LxqtmenudataConan(ConanFile):
    name = "lxqt-menu-data"
    version = "2.4.0.1"
    description = "lxqt-menu-data 2.4.0"
    license = "MIT"
    homepage = "https://github.com/lxqt/lxqt-menu-data"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    # Pure data package: no options, no build steps

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        src_root = os.path.join(self.source_folder, "menu")

        # Install .menu definitions into share/menus/
        menus_dst = os.path.join(self.package_folder, "share", "menus")
        os.makedirs(menus_dst, exist_ok=True)
        for f in os.listdir(os.path.join(src_root)):
            if f.endswith(".menu"):
                shutil.copy2(os.path.join(src_root, f), menus_dst)

        # Install desktop-directories (.directory.in files)
        dd_src = os.path.join(src_root, "desktop-directories")
        dd_dst = os.path.join(self.package_folder, "share", "desktop-directories")
        os.makedirs(dd_dst, exist_ok=True)
        for f in os.listdir(dd_src):
            if f.endswith(".directory.in"):
                # Rename .directory.in -> .directory
                dst_name = f.replace(".directory.in", ".directory")
                shutil.copy2(os.path.join(dd_src, f), os.path.join(dd_dst, dst_name))

    def package_info(self):
        # Data package: no libraries or headers to link against.
        pass