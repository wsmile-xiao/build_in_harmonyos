#!/usr/bin/env python3
"""Conan recipe for sha3sum 1.2.5 — Makefile-based build (no configure).

sha3sum is a command-line tool (not a library) that computes
SHA-3 / Keccak family hash sums. It depends on libkeccak.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Sha3SumConan(ConanFile):
    name = "sha3sum"
    version = "1.2.5"
    description = "SHA-3 / Keccak family hash sum command-line tools"
    license = "MIT"
    homepage = "https://github.com/maandree/sha3sum"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libkeccak/1.4.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Use Conan's built-in get() method — handles download + sha256 verification.
        # OHOS has non-standard CA certificate paths; set SSL_CERT_FILE so that
        # HTTPS downloads verify correctly (instead of disabling SSL verification).
        try:
            import certifi
            ca_file = certifi.where()
        except ImportError:
            import ssl
            ca_file = ssl.get_default_verify_paths().openssl_cafile
        if ca_file and os.path.exists(ca_file):
            os.environ.setdefault("SSL_CERT_FILE", ca_file)
            os.environ.setdefault("CURL_CA_BUNDLE", ca_file)
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No AutotoolsToolchain — this project uses a plain Makefile.
        # We pass compiler flags via environment variables / make args.
        pass

    @property
    def _opt_flags(self):
        if self.settings.build_type == "Debug":
            return "-fPIC -O0 -g"
        return "-fPIC -O2"

    def build(self):
        apply_conandata_patches(self)
        # Build using make with overridden variables.
        # PREFIX, CPPFLAGS, LDFLAGS are passed via make args (not patch)
        # to keep the patch portable (no hardcoded absolute paths).
        # R32: platform compatibility — works on both Linux and OHOS.
        keccak_inc = self.dependencies["libkeccak"].cpp_info.includedirs[0]
        keccak_lib = self.dependencies["libkeccak"].cpp_info.libdirs[0]
        self.run(
            f'make -j1 CC=clang '
            f'CFLAGS="{self._opt_flags}" '
            f'CPPFLAGS="-I{keccak_inc}" '
            f'LDFLAGS="-L{keccak_lib} -lkeccak"',
            cwd=self.source_folder,
        )

    def package(self):
        # Install to package_folder directly so bin/ is at the top level.
        # This ensures conan-verify G3/G4 can find the artifacts.
        self.run(
            f'make install PREFIX={self.package_folder} '
            f'DESTDIR=""',
            cwd=self.source_folder,
        )

    def package_info(self):
        # sha3sum is a command-line tool, not a library
        self.cpp_info.libs = []
        # Expose bin directory for consumers
        self.cpp_info.bindirs = ["bin"]
