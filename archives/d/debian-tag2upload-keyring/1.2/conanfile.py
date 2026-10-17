#!/usr/bin/env python3
"""Conan recipe for debian-tag2upload-keyring 1.2 — architecture-independent data.

This package ships the OpenPGP public keyring used by the Debian tag2upload
service: binary keyring `debian-tag2upload.pgp`. Pure data (no compilation,
no binaries → no commands.json, same model as iso-codes).

Platform adaptations for OHOS:
  1. No build needed — upstream is keyring bytes + shell test helpers.
  2. Installed to share/keyrings/debian-tag2upload.pgp so consumers can point
     sosumi/apt-equivalent or gpgv at the keyring path (R34 consumer view:
     python structural verification of the OpenPGP packet stream).

R28: test_package/ exists.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class DebianTag2UploadKeyringConan(ConanFile):
    name = "debian-tag2upload-keyring"
    version = "1.2"
    description = "OpenPGP signing key for the Debian tag2upload service"
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/dgit-team/debian-tag2upload-keyring"
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
        # Keyring data — nothing to compile.
        pass

    def package(self):
        src = self.source_folder
        copy(self, "debian-tag2upload.pgp", src=src,
             dst=os.path.join(self.package_folder, "share", "keyrings"),
             keep_path=False)
        copy(self, "README.md", src=src,
             dst=os.path.join(self.package_folder, "share", "doc",
                              "debian-tag2upload-keyring"),
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
        keyrings = os.path.join(self.package_folder, "share", "keyrings")
        if os.path.isdir(keyrings):
            self.runenv_info.append_path(
                "OPENPGP_KEYRING_DIR", keyrings)