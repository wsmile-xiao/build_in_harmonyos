#!/usr/bin/env python3
"""Conan recipe — proxytunnel 1.13.0

proxytunnel builds generic tunnels through HTTPS proxies using the HTTP
CONNECT method, with optional SSL/TLS encryption (-e/-E/-X) provided by
OpenSSL. Single self-contained executable, GPL-2.0.

Build system: plain GNU Makefile (no configure script). The upstream
Makefile exposes CC/CFLAGS/LDFLAGS as overridable make variables, so the
cross toolchain + OpenSSL paths are injected on the make command line
(R33: from Conan conf, never bare shell env vars).

Upstream: https://github.com/proxytunnel/proxytunnel (tag v1.13.0)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ProxytunnelConan(ConanFile):
    name = "proxytunnel"
    version = "1.13.0"
    description = "Build generic tunnels through HTTPS proxies using HTTP authentication (CONNECT + optional SSL/TLS)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/proxytunnel/proxytunnel"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OpenSSL is the only dependency (W0: prebuilt openssl/3.5.6.1
        # verified on ohpcd) — provides the -e/-E/-X SSL/TLS tunnels.
        self.requires("openssl/3.5.6.1")

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf, never bare ${CC} shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # OpenSSL flags from the Conan dependency (static libssl.a/libcrypto.a).
        # The upstream Makefile falls back to bare `-lssl -lcrypto` when
        # pkg-config cannot find openssl (no system openssl on OHOS), and its
        # `LDFLAGS += $(SSL_LIBS)` has no effect once LDFLAGS is set on the
        # make command line — so everything is passed explicitly here.
        openssl = self.dependencies["openssl"]
        ssl_inc = os.path.join(openssl.package_folder, "include")
        ssl_lib = os.path.join(openssl.package_folder, "lib")
        opt = "-O0 -g" if self.settings.build_type == "Debug" else "-O2"
        # R9: -j1 for this small single-binary project
        self.run(
            f'make -j1 CC="{cc}" '
            f'CFLAGS="-fPIC {opt} -I{ssl_inc}" '
            f'LDFLAGS="-L{ssl_lib} -lssl -lcrypto"',
            cwd=self.source_folder,
        )

    def package(self):
        # `make install` also drives docs/ (man page built with asciidoc +
        # xmlto, unavailable on OHOS/CI) — so package the single binary and
        # license files directly.
        copy(self, "proxytunnel", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
