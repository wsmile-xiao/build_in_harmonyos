#!/usr/bin/env python3
"""Conan recipe — reaver 1.6.6

A brute force attack tool against Wifi Protected Setup (WPS) registrar PINs.
Homepage: https://github.com/t6x/reaver-wps-fork-t6x
License: GPL-2.0
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ReaverConan(ConanFile):
    name = "reaver"
    version = "1.6.6"
    description = "Brute force attack against Wifi Protected Setup PINs"
    license = "GPL-2.0"
    homepage = "https://github.com/t6x/reaver-wps-fork-t6x"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")

        # Inject libpcap include and lib paths for defs.h <pcap.h>
        dep = self.dependencies["libpcap"]
        tc.extra_cflags.append(f"-I{dep.cpp_info.includedirs[0]}")
        tc.extra_ldflags.append(f"-L{dep.cpp_info.libdirs[0]}")


        # Note: -I, -L, -static flags are already set via tc.extra_cflags
        # and tc.extra_ldflags above. Do NOT also set CFLAGS/LDFLAGS as
        # configure args — that would override the toolchain's own flags
        # (e.g. --sysroot, -target, -g for Debug builds) set by Conan.
        tc.generate()

    def build(self):
        import os
        from conan.tools.files import patch
        # Iterate patches: 0001-shebang-umask only for OHOS, 0002-ualarm-fix for both
        for p in self.conan_data["patches"]:
            if p["patch_file"] == "patches/0001-shebang-umask.patch" and self.settings.os != "OHOS":
                continue
            pf = os.path.join(self.export_sources_folder, p["patch_file"])
            patch(self, patch_file=pf)

        # Run configure and make in src/ subdirectory
        autotools = Autotools(self)
        autotools.configure(build_script_folder="src")
        # Copy config.mak to src/ where the Makefile expects it
        import shutil
        shutil.copy(
            os.path.join(self.build_folder, "config.mak"),
            os.path.join(self.source_folder, "src", "config.mak")
        )
        # make in src/ where Makefile is
        self.run("make -C ../src -j1", env="conanbuild")

    def package(self):
        copy(self, "reaver", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "wash", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []