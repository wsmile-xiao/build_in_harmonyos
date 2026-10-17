#!/usr/bin/env python3
"""Conan recipe for bearssl 0.6 on HarmonyOS PC.

BearSSL is an optimized SSL/TLS library for embedded systems, pure C
with no external dependencies. It uses a custom Makefile build system
with conf/<config>.mk configuration files — no standard configure/make install.

Source: official git repo at https://www.bearssl.org/git/BearSSL (tag v0.6).
No tarball release exists; we clone via the Git SCM tool.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.scm import Git


class BearsslConan(ConanFile):
    name = "bearssl"
    version = "0.6"
    description = "Optimized SSL/TLS library for embedded systems, pure C, no external dependencies"
    license = "MIT"
    homepage = "https://www.bearssl.org/"
    url = "https://www.bearssl.org/git/BearSSL"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        git = Git(self)
        git.clone("https://www.bearssl.org/git/BearSSL", target=".")
        git.checkout(commit="v0.6")

    def build(self):
        apply_conandata_patches(self)

        # Create OHOS build config based on UnixClang.mk
        ohos_mk = """\
# Configuration for building on OpenHarmony (OHOS) with clang.
include conf/Unix.mk

BUILD = build_ohos
CC = clang
LD = clang
LDDLL = clang
AR = llvm-ar
"""
        save(self, os.path.join(self.source_folder, "conf", "Ohos.mk"), ohos_mk)

        # Build: static lib, shared lib, tools, and tests
        self.run("make CONF=Ohos", cwd=self.source_folder)

    def package(self):
        # Headers
        copy(self, "*.h", src=os.path.join(self.source_folder, "inc"),
             dst=os.path.join(self.package_folder, "include"))

        # Libraries
        build_dir = os.path.join(self.source_folder, "build_ohos")
        copy(self, "libbearssl.a", src=build_dir,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libbearssl.so", src=build_dir,
             dst=os.path.join(self.package_folder, "lib"))

        # brssl command-line tool
        copy(self, "brssl", src=build_dir,
             dst=os.path.join(self.package_folder, "bin"))

        # License
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["bearssl"]
        if self.options.shared:
            self.cpp_info.defines = ["BEARSSL_DLL"]
