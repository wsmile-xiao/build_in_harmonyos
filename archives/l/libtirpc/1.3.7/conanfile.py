#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libtirpc, libtirpc, 1.3.7, TI-RPC (Transport Independent RPC) library - 提供现代的RPC实现，支持TCP和UDP传输协议, BSD-3-Clause, https://sourceforge.net/projects/libtirpc/
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibtirpcConan(ConanFile):
    name = "libtirpc"
    version = "1.3.7"
    description = "TI-RPC (Transport Independent RPC) library - 提供现代的RPC实现，支持TCP和UDP传输协议"
    license = "BSD-3-Clause"
    homepage = "https://sourceforge.net/projects/libtirpc/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-gssapi")
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix HMDFS umask: config.status uses umask 077 which causes Permission denied
        # on HMDFS when creating temp directories. Fix it in configure before running.
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r") as f:
            content = f.read()
        content = content.replace("umask 077", "umask 000")
        with open(configure_path, "w") as f:
            f.write(content)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["tirpc"]
        self.cpp_info.includedirs = ["include", "include/tirpc"]
        self.cpp_info.resdirs = []
