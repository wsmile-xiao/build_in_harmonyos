#!/usr/bin/env python3
"""Conan recipe for HAProxy 3.2.0 on OpenHarmony.

HAProxy is a high-performance TCP/HTTP load balancer built with a custom
Makefile-based build system. This recipe builds it for the OHOS aarch64
platform using TARGET=linux-musl with OpenSSL, zlib, and PCRE2 support.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class HaproxyConan(ConanFile):
    name = "haproxy"
    version = "3.2.0"
    description = "Reliable, High Performance TCP/HTTP Load Balancer"
    license = "GPL-2.0-or-later"
    homepage = "https://www.haproxy.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1")
        self.requires("pcre2/10.47")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"haproxy does not support os={self.settings.os}"
            )

        # Get compiler from Conan profile conf (R33: avoid bare shell env vars).
        # Fallback to "clang" if conf not set (e.g. local dev without profile).
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(compilers, dict):
            cc = compilers.get("c", "clang")
        else:
            cc = "clang"

        # Get dependency paths from conan deps.
        openssl_info = self.dependencies["openssl"].cpp_info
        zlib_info = self.dependencies["zlib"].cpp_info
        pcre2_info = self.dependencies["pcre2"].cpp_info

        openssl_inc = openssl_info.aggregated_components().includedirs[0]
        openssl_lib = openssl_info.aggregated_components().libdirs[0]
        zlib_inc = zlib_info.aggregated_components().includedirs[0]
        zlib_lib = zlib_info.aggregated_components().libdirs[0]
        pcre2_inc = pcre2_info.aggregated_components().includedirs[0]
        pcre2_lib = pcre2_info.aggregated_components().libdirs[0]

        src = self.source_folder.replace("\\", "/")

        self.run(
            f"cd '{src}' && make haproxy TARGET=linux-musl CC={cc}"
            f" USE_OPENSSL=1 SSL_INC={openssl_inc} SSL_LIB={openssl_lib}"
            f" USE_ZLIB=1 ZLIB_INC={zlib_inc} ZLIB_LIB={zlib_lib}"
            f" USE_PCRE2=1 USE_PCRE2_JIT=1 PCRE2_INC={pcre2_inc} PCRE2_LIB={pcre2_lib}"
            f" USE_PROMEX=1"
            f" 'CFLAGS=-fPIC -O2'"
            f" -j1",
            env="conanbuild",
        )

    def package(self):
        # Copy the haproxy binary to bin/.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        src_bin = os.path.join(self.source_folder, "haproxy")
        if os.path.isfile(src_bin):
            shutil.copy(src_bin, os.path.join(bin_dir, "haproxy"))
            shutil.copymode(src_bin, os.path.join(bin_dir, "haproxy"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.define_path("PATH", os.path.join(self.package_folder, "bin"))
