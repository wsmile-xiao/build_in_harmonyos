#!/usr/bin/env python3
"""Conan recipe — dmg2img 1.6.7 (raw Makefile, CLI application).

Converts Apple compressed DMG archives to standard IMG/raw format.
Handles zlib, bzip2 compressed dmg images. Also builds vfdecrypt for
encrypted DMG decryption (OpenSSL 1.1.1+ API compatibility).

Source: http://vu1tur.eu.org/tools/ (GitHub mirror: citruz/dmg2img)
License: GPL-2.0

Patches:
  0001-Makefile.patch    — LZFSE conditional, cross-compile CC/CFLAGS support
  0002-dmg2img.c.patch   — LZFSE code guarded by HAVE_LZFSE
  0003-dmg2img.h.patch   — BT_LZFSE define guarded by HAVE_LZFSE
  0004-vfdecrypt.c.patch — OpenSSL 1.1.1 API compatibility (EVP_CIPHER_CTX/HMAC_CTX)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Dmg2ImgConan(ConanFile):
    name = "dmg2img"
    version = "1.6.7"
    description = "Convert Apple DMG disk images to IMG/raw format"
    license = "GPL-2.0"
    homepage = "https://github.com/citruz/dmg2img"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")
        self.requires("openssl/1.1.1w")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "dmg2img is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        compiler_executables = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = compiler_executables.get("c", "clang")

        # Build CFLAGS from dependency include dirs
        cflags = ["-O2", "-Wall"]
        ldflags = []
        for dep_name in ["zlib", "bzip2", "openssl"]:
            dep = self.dependencies[dep_name]
            cflags.extend(f"-I{d}" for d in dep.cpp_info.includedirs)
            ldflags.extend(f"-L{d}" for d in dep.cpp_info.libdirs)

        cflags_str = " ".join(cflags)
        ldflags_str = " ".join(ldflags) if ldflags else ""

        # R9: Always use -j1
        self.run(f'cd "{self.source_folder}" && make CC="{cc}" CFLAGS="{cflags_str}" LDFLAGS="{ldflags_str}" -j1')

    def package(self):
        # Copy built binaries to bin/
        copy(self, "dmg2img", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "vfdecrypt", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # dmg2img is a standalone CLI tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure binaries are on PATH for VirtualRunEnv (test_package)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
