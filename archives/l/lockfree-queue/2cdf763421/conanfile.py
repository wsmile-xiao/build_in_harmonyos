#!/usr/bin/env python3
"""Conan recipe for lockfree-queue (Yuzhong Wen, MIT).

A simple lock-free queue implementation based on
John D. Valois "Implementing Lock-Free Queues".

Build system: plain Makefile (no configure, no install target).
The recipe compiles pkt_queue.c into a static library and
installs pkt_queue.h + libpkt_queue.a.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class LockfreeQueueConan(ConanFile):
    name = "lockfree-queue"
    version = "2cdf763421"
    description = "A simple lock-free queue implementation (Valois algorithm)"
    license = "MIT"
    homepage = "https://github.com/supermartian/lockfree-queue"
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

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")
        if self.options.shared:
            raise ConanInvalidConfiguration("lockfree-queue only supports static build")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # R33: compiler flags come from Conan profile via GnuToolchain
    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cc = self.conf_info.get("tools.build:compiler_executables", {}).get("c", "clang")
        with chdir(self, self.source_folder):
            self.run(f"{cc} -fPIC -O2 -c pkt_queue.c -o pkt_queue.o", env="conanbuild")
            self.run("ar rcs libpkt_queue.a pkt_queue.o", env="conanbuild")

    def package(self):
        copy(self, "pkt_queue.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "libpkt_queue.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["pkt_queue"]
