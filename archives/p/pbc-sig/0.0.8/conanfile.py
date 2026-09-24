#!/usr/bin/env python3
"""Conan recipe — pbc-sig 0.0.8 (Autotools)."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PbcSigConan(ConanFile):
    name = "pbc-sig"
    version = "0.0.8"
    description = "Pairing-Based Cryptography signature schemes library (BLS, BB, BBS, Cha-Cheon IBS)"
    license = "GPL-3.0"
    homepage = "https://github.com/mag1c1an1/pbc_sig"
    url = "https://github.com/mag1c1an1/pbc_sig/releases/download/v0.0.8/pbc_sig-0.0.8.tar.gz"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("pbc/1.0.0")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])

        pbc = self.dependencies["pbc"].cpp_info
        gmp = self.dependencies["gmp"].cpp_info
        environment = toolchain.environment()
        environment.append("CPPFLAGS", "-I{}".format(pbc.includedirs[0]))
        environment.append("CPPFLAGS", "-I{}".format(gmp.includedirs[0]))
        environment.append("LDFLAGS", "-L{}".format(pbc.libdirs[0]))
        environment.append("LDFLAGS", "-L{}".format(gmp.libdirs[0]))
        toolchain.generate(environment)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for f in os.listdir(libdir):
                if f.endswith(".la"):
                    os.remove(os.path.join(libdir, f))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["pbc_sig"]
        self.cpp_info.set_property("cmake_file_name", "pbc_sig")
        self.cpp_info.set_property("cmake_target_name", "pbc_sig::pbc_sig")
        self.cpp_info.set_property("pkg_config_name", "pbc_sig")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
