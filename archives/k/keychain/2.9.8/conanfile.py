#!/usr/bin/env python3
"""Conan recipe — keychain 2.9.8

keychain is a SSH/GPG key agent manager written as a Bourne shell script.
Build system: plain Makefile (no configure script).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class KeychainConan(ConanFile):
    name = "keychain"
    version = "2.9.8"
    description = "SSH/GPG key agent manager - Bourne shell script implementation"
    license = "GPL-2.0"
    homepage = "https://github.com/danielrobbins/keychain"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        check_types_os = ["Linux", "OHOS"]
        if self.settings.os not in check_types_os:
            raise ConanInvalidConfiguration(f"{self.name} only supports {check_types_os}")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception as e:
            self.output.warning(f"Online download failed ({e}), falling back to local file copy")
            local_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "keychain-2.9.8.tar.gz"
            )
            if not os.path.isfile(local_path):
                local_path = "/storage/Users/currentUser/.opendesk/apps/skills/resources/harmony-compile/archives/k/keychain/2.9.8/keychain-2.9.8.tar.gz"
            if os.path.isfile(local_path):
                get(self, "file://" + local_path, sha256=self.conan_data["sources"]["sha256"], strip_root=True)
            else:
                raise

    def build(self):
        apply_conandata_patches(self)
        self.run(f"make -C {self.build_folder} PREFIX={self.package_folder}")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        compdir = os.path.join(self.package_folder, "share", "bash-completion", "completions")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)
        os.makedirs(compdir, exist_ok=True)
        copy(self, "keychain", src=self.build_folder, dst=bindir)
        copy(self, "keychain.1", src=self.build_folder, dst=mandir)
        copy(self, "keychain.bash", src=os.path.join(self.build_folder, "completions"), dst=compdir)

    def package_info(self):
        self.cpp_info.libs = []
