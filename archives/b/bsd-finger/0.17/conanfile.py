#!/usr/bin/env python3
"""Conan recipe — bsd-finger 0.17 (netkit finger client + fingerd daemon)

bsd-finger is the NetKit finger program, printing user information
(finger) and the associated remote finger daemon (in.fingerd).
Build system: netkit confgen configure + Makefile (not GNU autotools).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    copy, get, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.layout import basic_layout


class BsdFingerConan(ConanFile):
    name = "bsd-finger"
    version = "0.17"
    description = "NetKit bsd-finger: finger client and in.fingerd daemon"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Distrotech/bsd-finger"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(compilers, dict):
            cc = compilers.get("c", "clang")
        else:
            cc = "clang"

        # netkit confgen configure: accepts --prefix and --with-c-compiler
        self.run(f"sh configure --prefix=/usr --with-c-compiler={cc}",
                 cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # finger client -> bin/
        copy(self, "finger",
             os.path.join(self.source_folder, "finger"),
             os.path.join(self.package_folder, "bin"))
        # fingerd -> sbin/, then rename to upstream install name in.fingerd
        copy(self, "fingerd",
             os.path.join(self.source_folder, "fingerd"),
             os.path.join(self.package_folder, "sbin"))
        os.rename(os.path.join(self.package_folder, "sbin", "fingerd"),
                  os.path.join(self.package_folder, "sbin", "in.fingerd"))
        # man pages
        copy(self, "finger.1",
             os.path.join(self.source_folder, "finger"),
             os.path.join(self.package_folder, "man", "man1"))
        copy(self, "fingerd.8",
             os.path.join(self.source_folder, "fingerd"),
             os.path.join(self.package_folder, "man", "man8"))
        os.rename(os.path.join(self.package_folder, "man", "man8", "fingerd.8"),
                  os.path.join(self.package_folder, "man", "man8", "in.fingerd.8"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []