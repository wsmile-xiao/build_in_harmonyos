#!/usr/bin/env python3
"""Conan recipe for bdw-gc 8.2.6 — Autotools build system.

bdw-gc (Boehm-Demers-Weiser Garbage Collector) is a conservative garbage
collector for C and C++. On HarmonyOS, pthread_setcancelstate and
pthread_cancel are not available in musl libc, so CANCEL_SAFE and
GC_HAVE_PTHREAD_EXIT are disabled via source patches.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BdwgcConan(ConanFile):
    name = "bdw-gc"
    version = "8.2.6"
    description = "Boehm-Demers-Weiser conservative garbage collector for C/C++"
    license = "MIT"
    homepage = "https://github.com/bdwgc/bdwgc"
    url = "https://github.com/bdwgc/bdwgc"

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
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # OHOS: Use bash as CONFIG_SHELL (zsh breaks autotools, E011)
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not self.options.shared:
            shared_args = "--enable-static --disable-shared"
        else:
            shared_args = "--enable-shared"
        self.run(f"CONFIG_SHELL={config_shell} CC={cc} {config_shell} ./configure {shared_args} --prefix=/")
        self.run("make -j1")
        # L1: Run upstream official test suite (make check)
        self.run("make check")

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["gc"]
        self.cpp_info.system_libs = ["pthread", "dl"]
