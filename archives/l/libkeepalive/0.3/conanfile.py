#!/usr/bin/env python3
"""Conan recipe for libkeepalive 0.3 (HarmonyOS PC / aarch64).

libkeepalive is a small LD_PRELOAD interposer library: it hooks socket() and
enables TCP keepalive on AF_INET/AF_INET6 SOCK_STREAM sockets
(SO_KEEPALIVE, plus TCP_KEEPCNT/TCP_KEEPIDLE/TCP_KEEPINTVL taken from the
KEEPCNT/KEEPIDLE/KEEPINTVL environment variables, and a KEEPALIVE=off escape
hatch). The upstream project is a plain GNU Make project without a configure
script; its only build product is src/libkeepalive.so.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibkeepaliveConan(ConanFile):
    name = "libkeepalive"
    version = "0.3"
    description = "LD_PRELOAD library that enables TCP keepalive for IPv4/IPv6 TCP sockets"
    license = "MIT"
    homepage = "http://libkeepalive.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    # The upstream Makefile can only build in-tree, so the sources are used in
    # place instead of being copied into the build folder.
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: take the compiler from the Conan toolchain, never from ${CC}.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # Only src/ is built. The upstream top-level Makefile additionally runs
        # `strip -s` on the copy it places in the source root; stripping removes
        # nothing that the dynamic linker needs, but it invalidates the OHOS
        # `.codesign` block, after which the loader silently ignores the library
        # as an LD_PRELOAD interposer. src/Makefile alone never strips.
        self.run(f"make -C src CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "libkeepalive.so", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["keepalive"]
