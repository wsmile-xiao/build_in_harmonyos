#!/usr/bin/env python3
"""Conan recipe for hcxtools 7.1.2 — capture-to-hash conversion tools.

hcxtools is a set of command-line tools that convert packets from
capture files (pcap/pcapng) to hash files for use with Hashcat or
John the Ripper.  Built as an application (executables only, no
shared library), using a plain Makefile that relies on pkg-config
for OpenSSL, libcurl, and zlib discovery.

Dependencies (resolved from OHOS Conan artifact repo):
  - openssl/3.5.6.1   (EVP MAC, crypto routines)
  - zlib/1.3.1.1       (gzip pcapng support)
  - curl/8.15.0        (online lookup tools: hcxhashtool, whoismac, wlancap2wpasec)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class HcxtoolsConan(ConanFile):
    name = "hcxtools"
    version = "7.1.2"
    description = "Tools to convert packets from capture files to hash files for Hashcat / John the Ripper"
    license = "MIT"
    homepage = "https://github.com/ZerBea/hcxtools"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")
        self.requires("zlib/1.3.1.1")
        self.requires("curl/8.15.0")

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = comp_execs.get("c", "clang")

        # The Makefile uses pkg-config to find openssl, libcurl, zlib.
        # PkgConfigDeps generates .pc files in self.generators_folder.
        # Set PKG_CONFIG_PATH explicitly so the Makefile's $(shell pkg-config ...)
        # calls can locate the conan-managed dependency .pc files.
        gen = self.generators_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(os.path.join(staging, "usr", "bin"), exist_ok=True)

        env = f"PKG_CONFIG_PATH={gen}"

        self.run(
            f"{env} make CC={cc} -j1",
            cwd=self.source_folder,
        )
        self.run(
            f"{env} make install CC={cc} PREFIX=/usr"
            f" DESTDIR={staging}",
            cwd=self.source_folder,
        )

        self._staging = staging

    def package(self):
        staging = getattr(self, "_staging", None)
        if not staging:
            return
        src_bin = os.path.join(staging, "usr", "bin")
        if os.path.isdir(src_bin):
            dst_bin = os.path.join(self.package_folder, "bin")
            os.makedirs(dst_bin, exist_ok=True)
            for f in os.listdir(src_bin):
                src_file = os.path.join(src_bin, f)
                if os.path.isfile(src_file):
                    shutil.copy2(src_file, os.path.join(dst_bin, f))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # System libs linked at build time (from pkg-config: openssl needs dl, pthread)
        self.cpp_info.system_libs = ["dl", "pthread"]
