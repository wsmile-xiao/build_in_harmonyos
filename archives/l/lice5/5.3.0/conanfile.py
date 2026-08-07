#!/usr/bin/env python3
"""Conan recipe — lice5 5.3.0 (pure IRC script resource package)

LiCe is a script designed for the ircII and EPIC irc clients; it radically
improves the usability of these clients, providing features and enhancements
that pioneered the way for a whole crowd of imitators.

This is a pure script resource package — no C/C++ code, no compilation.
"Installation" consists of copying script files to share/lice5/ for the
epic5 IRC client to load at runtime.

Platform compatibility:
  - No C code, no ELF binaries, no shebang rewriting needed
  - Scripts are loaded by epic5 at runtime, not executed directly
  - R26 (static linking) does not apply — no native code
  - R38 (commands.json) not needed — no command-line executables
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class Lice5Conan(ConanFile):
    name = "lice5"
    version = "5.3.0"
    description = "LiCe script for epic5/ircII IRC clients (pure script resource package)"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/lice5"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.output.info("Pure IRC script resource package; no native build step required")

    def package(self):
        # Install script resources to share/lice5/, preserving directory structure.
        # Source tarball layout: lice5/{lice,help,logos,pics,themes,userhelp}
        resource_dir = os.path.join(self.package_folder, "share", "lice5")
        # Main scripts (lice.* files)
        copy(self, "*", src=os.path.join(self.source_folder, "lice"),
             dst=os.path.join(resource_dir, "lice"))
        # Help files
        copy(self, "*", src=os.path.join(self.source_folder, "help"),
             dst=os.path.join(resource_dir, "help"))
        # Logos
        copy(self, "*", src=os.path.join(self.source_folder, "logos"),
             dst=os.path.join(resource_dir, "logos"))
        # Pics
        copy(self, "*", src=os.path.join(self.source_folder, "pics"),
             dst=os.path.join(resource_dir, "pics"))
        # Themes
        copy(self, "*", src=os.path.join(self.source_folder, "themes"),
             dst=os.path.join(resource_dir, "themes"))
        # User help
        copy(self, "*", src=os.path.join(self.source_folder, "userhelp"),
             dst=os.path.join(resource_dir, "userhelp"))

    def package_id(self):
        # Pure script package — identical across all configurations
        self.info.clear()

    def package_info(self):
        resource_dir = os.path.join(self.package_folder, "share", "lice5")
        # Expose resource directory for epic5 to locate lice scripts
        self.runenv_info.prepend_path("LICE5_DIR", resource_dir)
        # No libraries or executables
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
