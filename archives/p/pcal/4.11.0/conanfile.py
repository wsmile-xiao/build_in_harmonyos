#!/usr/bin/env python3
"""Conan recipe for pcal 4.11.0.

pcal is a command-line calendar generator. The upstream release uses a plain
Makefile and builds a single C executable.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PcalConan(ConanFile):
    name = "pcal"
    version = "4.11.0"
    description = "Command-line PostScript and HTML calendar generator"
    license = "custom-permissive"
    homepage = "https://pcal.sourceforge.net"
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
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # Upstream Makefile hardcodes /usr/bin/gcc and overrides environment
        # CFLAGS. Pass both on the command line and avoid OHOS FIFO jobserver.
        cflags = "-fPIC -O2 -Wall -W"
        self.run(
            "make -j1 CC={} CFLAGS={} PACK=:".format(shlex.quote(cc), shlex.quote(cflags)),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(self, "pcal", src=os.path.join(self.source_folder, "exec"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "ReadMe.txt", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "doc", "pcal"), keep_path=False)

        man_src = os.path.join(self.source_folder, "doc", "pcal.man")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        if os.path.isfile(man_src):
            os.makedirs(man_dir, exist_ok=True)
            shutil.copy2(man_src, os.path.join(man_dir, "pcal.1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
