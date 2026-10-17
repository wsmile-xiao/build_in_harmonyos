#!/usr/bin/env python3
"""Conan recipe for axel 2.17.14 — lightweight CLI download accelerator.

Axel is a command-line tool, not a library. It uses autotools (configure + make)
and depends on OpenSSL for TLS/SSL support.

OHOS platform adaptations:
  - config.guess/config.sub patched for OHOS triplet detection
  - compat-android.h extended for __OHOS__ (musl pthread_cancel compat)
  - configure umask 077→022 for HMDFS permission compatibility
"""
from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class AxelConan(ConanFile):
    name = "axel"
    version = "2.17.14"
    description = "Lightweight CLI download accelerator"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/axel-download-accelerator/axel"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

        # Set SSL-specific flags from openssl dependency for configure
        openssl = self.dependencies["openssl"]
        openssl_folder = openssl.package_folder
        ssl_cflags = f"-I{openssl_folder}/include"
        ssl_libs = f"-L{openssl_folder}/lib -lssl -lcrypto"

        env = Environment()
        env.define("SSL_CFLAGS", ssl_cflags)
        env.define("SSL_LIBS", ssl_libs)
        envvars = env.vars(self)
        envvars.save_script("conan_ssl_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # axel is a CLI tool — declare bindirs for consumers
        self.cpp_info.bindirs = ["bin"]
