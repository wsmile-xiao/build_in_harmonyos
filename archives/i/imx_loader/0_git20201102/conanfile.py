#!/usr/bin/env python3
"""Conan recipe for boundarydevices/imx_usb_loader 0_git20201102."""

import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class ImxLoaderConan(ConanFile):
    name = "imx_loader"
    version = "0_git20201102"
    description = "NXP i.MX USB and UART bootloader utilities"
    license = "LGPL-2.1-only"
    homepage = "https://github.com/boundarydevices/imx_usb_loader"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        pkg_config_path = shlex.quote(self.generators_folder)
        libusb_include_root = os.path.join(
            self.dependencies["libusb"].package_folder, "include"
        )
        cflags = (
            "-O2 -fPIE -Wall -Wstrict-prototypes -Wno-trigraphs -I{}".format(
                shlex.quote(libusb_include_root)
            )
        )

        # The upstream Makefile discovers libusb through pkg-config. Conan's
        # PkgConfigDeps writes its .pc file to generators_folder; expose that
        # directory explicitly because VirtualBuildEnv does not add it here.
        # The upstream include spells `libusb-1.0/libusb.h`, while libusb's
        # pkg-config include flag points inside include/libusb-1.0; add its
        # parent include directory to preserve that source include spelling.
        self.run(
            "PKG_CONFIG_PATH={} make -j1 CC={} CFLAGS={} LDFLAGS={} "
            "bindir=/bin sysconfdir=/etc".format(
                pkg_config_path,
                shlex.quote(cc),
                shlex.quote(cflags),
                shlex.quote("-pie -Wl,-z,relro,-z,now"),
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )

        # Upstream's tests/Makefile compares simulator output against three
        # checked-in golden transcripts; no physical board or USB access is used.
        self.run(
            "PKG_CONFIG_PATH={} make -j1 tests bindir=/bin sysconfdir=/etc".format(
                pkg_config_path
            ),
            cwd=self.source_folder,
            env="conanrun",
        )

    def package(self):
        # Install a relocatable layout: bin/ and etc/ sit at package root, and
        # the upstream executable searches ../etc/imx-loader.d relative to bin/.
        self.run(
            "make -j1 DESTDIR={} prefix= bindir=/bin sysconfdir=/etc install".format(
                shlex.quote(self.package_folder)
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
