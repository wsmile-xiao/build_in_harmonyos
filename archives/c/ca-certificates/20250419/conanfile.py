#!/usr/bin/env python3
"""Conan recipe — ca-certificates (Mozilla CA certificate bundle).

This is a data-only package: no compilation needed.
The build step runs certdata2pem.py to convert Mozilla's certdata.txt
into PEM-format certificate files.

Patch 0001 makes the cryptography import optional so certdata2pem.py
works on HarmonyOS where the Rust-based cryptography .so cannot load
(ELF signature requirement). All certificates are still generated;
only the non-fatal expiration check is skipped when cryptography is
unavailable.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CACertificatesConan(ConanFile):
    name = "ca-certificates"
    version = "20250419"
    description = "Mozilla CA certificate bundle — trusted root certificates for TLS/SSL"
    license = "MPL-2.0"
    homepage = "https://salsa.debian.org/debian/ca-certificates"

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        mozilla_dir = os.path.join(self.source_folder, "mozilla")
        self.run(f"cd {mozilla_dir} && python3 certdata2pem.py")

    def package(self):
        mozilla_dir = os.path.join(self.source_folder, "mozilla")
        sbin_dir = os.path.join(self.source_folder, "sbin")

        copy(self, "*.crt", mozilla_dir,
             os.path.join(self.package_folder, "share", "ca-certificates", "mozilla"))
        copy(self, "update-ca-certificates", sbin_dir,
             os.path.join(self.package_folder, "sbin"))
        copy(self, "update-ca-certificates.8", sbin_dir,
             os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
        self.cpp_info.resdirs = ["share"]
