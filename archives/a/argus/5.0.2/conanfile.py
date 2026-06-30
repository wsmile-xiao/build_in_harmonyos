#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Argus, argus, 5.0.2, argus 5.0.2, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ArgusConan(ConanFile):
    name = "argus"
    version = "5.0.2"
    description = "Argus - Audit Record Generation and Utilization System"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/openargus/argus"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # Build in source directory: argus Makefile depends on Makefile.in
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # 鸿蒙不支持 mkfifo jobserver, 用 -j1
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove Perl/shell scripts that can't execute on HarmonyOS
        import glob
        for f in glob.glob(os.path.join(self.package_folder, "bin", "argus-*")):
            os.remove(f)
        argusbug = os.path.join(self.package_folder, "bin", "argusbug")
        if os.path.exists(argusbug):
            os.remove(argusbug)
        # Copy static library argus_common.a as libargus.a (make install doesn't install it)
        copy(self, "argus_common.a",
             src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        os.rename(
            os.path.join(self.package_folder, "lib", "argus_common.a"),
            os.path.join(self.package_folder, "lib", "libargus.a"))
        # Copy header files (make install doesn't install them)
        copy(self, "*.h",
             src=os.path.join(self.build_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["argus"]
        self.cpp_info.system_libs = ["pcap", "z", "m", "pthread"]
