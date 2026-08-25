#!/usr/bin/env python3
"""Conan recipe for qdbm 1.8.78 — Autotools (in-source build).

QDBM's hand-written configure does not support out-of-source builds,
so we use self.run() instead of Conan's Autotools helper.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.gnu import AutotoolsToolchain


class QdbmConan(ConanFile):
    name = "qdbm"
    version = "1.8.78"
    description = "QDBM (Quick Database Manager) is an embedded database library providing hash and B+ tree key-value storage"
    license = "LGPL-2.1"
    homepage = "https://dbmx.net/qdbm/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/-/tree/main/archives/q/qdbm/1.8.78"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # qdbm's configure does not support out-of-source builds
        conf_args = ["--prefix=/"]
        if self.options.shared:
            conf_args.append("--enable-shared")
        else:
            conf_args.append("--enable-static")
            conf_args.append("--disable-shared")
        self.run("./configure {}".format(" ".join(conf_args)), env="conanbuild")
        self.run("make -j1", env="conanbuild")

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder), env="conanbuild")
        # qdbm's configure ignores --disable-shared, always builds .so.
        # Remove shared libs in static mode so test_package links statically.
        if not self.options.shared:
            rm(self, "libqdbm.so*", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["qdbm"]
