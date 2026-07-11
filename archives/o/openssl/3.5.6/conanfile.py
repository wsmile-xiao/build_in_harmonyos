#!/usr/bin/env python3
"""Conan recipe — OpenSSL 3.5.6 (custom-perl build system).

OpenSSL uses `perl ./Configure` (capital C) instead of standard ./configure.
Build system: custom-perl (Configure + make)

Key rules:
  - R9:  Use make -j1 (not -j$(nproc))
  - R26: OpenSSL IS a system-name library (libssl, libcrypto clash with system /lib).
          Must use `no-shared` to force static-only build, preventing .so pollution.
  - R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OpensslConan(ConanFile):
    name = "openssl"
    version = "3.5.6"
    description = "Industry-standard TLS/SSL and cryptographic library"
    license = "Apache-2.0"
    homepage = "https://www.openssl.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: All dependencies MUST use @ohpcd/stable format
        # OpenSSL can optionally use zlib for compression
        # self.requires("zlib/1.3.1@ohpcd/stable")
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R32: settings.os check must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        # OpenSSL uses perl ./Configure (capital C), not ./configure
        # no-asm: OHOS platform has no assembly support (E006)
        # linux-aarch64: built-in target for aarch64
        prefix = self.package_folder
        openssldir = os.path.join(prefix, "ssl")

        configure_cmd = (
            f"perl ./Configure "
            f"--prefix={prefix} "
            f"--openssldir={openssldir} "
            f"no-asm "
            f"no-shared "
            f"linux-aarch64"
        )
        # Run from source folder where Configure script exists
        self.run(configure_cmd, cwd=self.source_folder)

        # R9: Use -j1 for safety
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # make install_sw installs software only (no docs) to --prefix
        # OpenSSL 3.5.6 source is missing some pod.in files (e.g. openssl-spkac.pod.in)
        # so make install fails during doc generation. install_sw skips docs.
        self.run("make install_sw", cwd=self.source_folder)

    def package_info(self):
        # OpenSSL provides libcrypto and libssl (not libopenssl)
        self.cpp_info.libs = ["ssl", "crypto"]
        # Add -ldl -pthread for linking
        self.cpp_info.system_libs = ["dl", "pthread"]
