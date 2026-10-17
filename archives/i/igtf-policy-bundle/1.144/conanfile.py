#!/usr/bin/env python3
"""Conan recipe — igtf-policy-bundle (IGTF Trust Anchor distribution).

This is a data-only package: no compilation needed.
The package installs the IGTF-accredited CA certificate bundle for
grid and research infrastructure trust anchors.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class IGTFPolicyBundleConan(ConanFile):
    name = "igtf-policy-bundle"
    version = "1.144"
    description = "IGTF Trust Anchor distribution — accredited CA certificate bundle for grid and research infrastructures"
    license = "CC-BY-3.0"
    homepage = "https://dist.igtf.net/distribution/igtf/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Data-only package: nothing to compile
        apply_conandata_patches(self)
        pass

    def package(self):
        top_dir = self.source_folder
        pkg_share = os.path.join(self.package_folder, "share", "igtf-policy-bundle")
        ac_dir = os.path.join(top_dir, "src", "accredited")
        ua_dir = os.path.join(top_dir, "src", "unaccredited")

        # Top-level files
        copy(self, "LICENSE", top_dir, pkg_share)
        copy(self, "CHANGES", top_dir, pkg_share)
        copy(self, "README.txt", top_dir, pkg_share)
        # Policy info files
        copy(self, "policy-igtf*.info", top_dir, pkg_share)
        # Accredited CA certificates and metadata
        copy(self, "*.pem", ac_dir, os.path.join(pkg_share, "accredited"))
        copy(self, "*.crl_url", ac_dir, os.path.join(pkg_share, "accredited"))
        copy(self, "*.signing_policy", ac_dir, os.path.join(pkg_share, "accredited"))
        copy(self, "*.namespaces", ac_dir, os.path.join(pkg_share, "accredited"))
        copy(self, "*.info", ac_dir, os.path.join(pkg_share, "accredited"))
        # Unaccredited CA certificates and metadata
        if os.path.isdir(ua_dir):
            copy(self, "*.pem", ua_dir, os.path.join(pkg_share, "unaccredited"))

    def package_info(self):
        self.cpp_info.resdirs = ["share"]