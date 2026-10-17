#!/usr/bin/env python3
"""Conan recipe for debian-ports-archive 2026.02.04 — architecture-independent data.

Ships the active/removed OpenPGP archive certificates of the debian-ports
archive (ASCII-armored key files). Pure data: no compilation, no binaries →
no commands.json (same model as iso-codes / debian-tag2upload-keyring).

Upstream source package is `debian-ports-archive-keyring`; the task software
name is `debian-ports-archive`.

Platform adaptations for OHOS:
  1. No build step — key files are copied verbatim under
     share/keyrings/debian-ports-archive/{active-keys,removed-keys}/.
  2. R34 consumer view: python test verifies every key file is a well-formed
     ASCII-armored OpenPGP public key block (BEGIN/END markers) and that the
     expected active/removed inventories are present.

R28: test_package/ exists.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class DebianPortsArchiveConan(ConanFile):
    name = "debian-ports-archive"
    version = "2026.02.04"
    description = "OpenPGP archive certificates of the debian-ports archive"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/aurel32/debian-ports-archive-keyring"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"

    # OHOS profile requires four settings (L0p gate); data still aligns
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Key data — nothing to compile.
        pass

    def package(self):
        src = self.source_folder
        base = os.path.join(self.package_folder, "share", "keyrings",
                            "debian-ports-archive")
        copy(self, "*", src=os.path.join(src, "active-keys"),
             dst=os.path.join(base, "active-keys"))
        copy(self, "*", src=os.path.join(src, "removed-keys"),
             dst=os.path.join(base, "removed-keys"))
        copy(self, "README", src=src,
             dst=os.path.join(self.package_folder, "share", "doc",
                              "debian-ports-archive"),
             keep_path=False)
        copy(self, "debian/copyright", src=src,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
        keyrings = os.path.join(self.package_folder, "share", "keyrings",
                                "debian-ports-archive")
        if os.path.isdir(keyrings):
            self.runenv_info.define("DEBIAN_PORTS_ARCHIVE_KEYS", keyrings)