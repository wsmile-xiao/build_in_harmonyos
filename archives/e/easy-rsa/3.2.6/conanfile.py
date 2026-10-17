#!/usr/bin/env python3
"""Conan recipe for easy-rsa 3.2.6 — a POSIX shell-based CA utility.

Easy-RSA is a pure shell script tool for managing PKI (Public Key Infrastructure).
No compilation is required; the build step replaces version placeholders in the
easyrsa script and the package step installs the script plus support files.

Runtime dependency: OpenSSL command-line tool (openssl binary in PATH).
"""
import os
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file, \
    export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class EasyRsaConan(ConanFile):
    name = "easy-rsa"
    version = "3.2.6"
    description = "Easy-RSA — a POSIX shell-based CA utility for managing PKI and X.509 certificates"
    license = "GPL-2.0-only"
    homepage = "https://github.com/OpenVPN/easy-rsa"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime dependency: easyrsa uses the openssl command-line tool
        self.requires("openssl/1.1.1w")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches (if any declared in conandata.yml)
        apply_conandata_patches(self)
        # Replace version placeholders in the easyrsa script, mirroring
        # the upstream build-dist.sh sed substitutions.
        easyrsa = os.path.join(self.source_folder, "easyrsa3", "easyrsa")
        date_str = time.strftime("%a %b %d %H:%M:%S %Z %Y")
        replace_in_file(self, easyrsa, "~VER~", str(self.version))
        replace_in_file(self, easyrsa, "~DATE~", date_str)
        replace_in_file(self, easyrsa, "~GITHEAD~", "unknown")

    def package(self):
        # Install the main easyrsa script
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "easyrsa", src=os.path.join(self.source_folder, "easyrsa3"),
             dst=bindir, keep_path=False)
        os.chmod(os.path.join(bindir, "easyrsa"), 0o755)

        # Install support files (openssl-easyrsa.cnf, vars.example, x509-types/)
        sharedir = os.path.join(self.package_folder, "share", "easy-rsa")
        copy(self, "openssl-easyrsa.cnf",
             src=os.path.join(self.source_folder, "easyrsa3"), dst=sharedir,
             keep_path=False)
        copy(self, "vars.example",
             src=os.path.join(self.source_folder, "easyrsa3"), dst=sharedir,
             keep_path=False)
        copy(self, "*",
             src=os.path.join(self.source_folder, "easyrsa3", "x509-types"),
             dst=os.path.join(sharedir, "x509-types"), keep_path=False)

        # Install documentation
        copy(self, "COPYING.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/easy-rsa"]
