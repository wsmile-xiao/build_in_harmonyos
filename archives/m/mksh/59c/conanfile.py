#!/usr/bin/env python3
"""Conan recipe — mksh 59c (MirBSD Korn Shell).

mksh uses a custom Build.sh script, not standard autotools.
This recipe enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MkshConan(ConanFile):
    name = "mksh"
    version = "59c"
    description = "MirBSD Korn Shell R59c"
    license = "MIT"
    homepage = "https://mbsd.evolvis.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF)
        # mksh uses Build.sh; static linking via -static in LDFLAGS (see build())
        pass

    def build(self):
        apply_conandata_patches(self)
        # mksh uses Build.sh, not standard autotools
        cc = os.environ.get("CC", "clang")
        # R26: static linking for terminal tools
        build_sh = os.path.join(self.source_folder, "Build.sh")
        self.run(f"CC={cc} LDFLAGS='-static' sh {build_sh} -r", cwd=self.source_folder)

    def package(self):
        # Install mksh binary and man pages from source folder
        copy(self, "mksh", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "mksh.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "lksh.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "dot.mkshrc", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "mksh", "examples"))

    def package_info(self):
        # mksh is a binary tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
