#!/usr/bin/env python3
"""Conan recipe for beanstalkd — a simple, fast work queue service.

beanstalkd uses a simple Makefile (no autotools/configure).
The Makefile detects the OS via `uname` and compiles the corresponding
platform file (e.g. harmonyos.c on HarmonyOS, linux.c on Linux).

Patches:
  0002-harmonyos.c.patch — HarmonyOS platform file (epoll-based, same as linux.c)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BeanstalkdConan(ConanFile):
    name = "beanstalkd"
    version = "1.13"
    description = "A simple, fast work queue service"
    license = "MIT"
    homepage = "https://beanstalkd.github.io/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = compilers.get("c", "clang")

        # beanstalkd uses a simple Makefile in the source folder.
        # The Makefile auto-detects OS via uname and compiles harmonyos.c on OHOS.
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Makefile: BINDIR=$(DESTDIR)$(PREFIX)/bin
        # Set PREFIX to package_folder so binary goes to $PACKAGE_FOLDER/bin/
        self.run(f"make install PREFIX={self.package_folder} -j1",
                 cwd=self.source_folder)

    def package_info(self):
        # beanstalkd is an executable — expose bin directory
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
