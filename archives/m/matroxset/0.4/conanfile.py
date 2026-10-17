#!/usr/bin/env python3
"""Conan recipe for matroxset 0.4."""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout
from conan.tools.files import get, patch, copy, download
from conan.tools.build import cross_building
from conan.tools.microsoft import is_msvc
from conan.tools.gnu import AutotoolsToolchain
import tempfile
import os


class MatroxsetConan(ConanFile):
    name = "matroxset"
    version = "0.4"
    description = "Matrox video capture/encoding utility"
    license = "GPL-2.0-only"
    homepage = "https://www.bglug.ca/matrox_tvout"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download and apply the Debian patch for format string fixes
        # The patch expects paths with "matroxset-0.4.orig/" and "matroxset-0.4/" prefixes
        # but strip_root=True extracts without prefix, so we need to manually adjust the patch
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            download(self, self.conan_data["patches"]["10-gcc.patch"]["url"], filename=f.name)
            # Read and fix the patch file paths
            with open(f.name, 'r') as pf:
                patch_content = pf.read()
            # Remove the "matroxset-0.4.orig/" and "matroxset-0.4/" prefixes
            patch_content = patch_content.replace("matroxset-0.4.orig/", "")
            patch_content = patch_content.replace("matroxset-0.4/", "")
            with open(f.name, 'w') as pf:
                pf.write(patch_content)
            patch(self, patch_file=f.name)
        os.unlink(f.name)

    def generate(self):
        # Generate toolchain to get proper ncurses flags
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # Use the generated conanbuild environment which has ncurses paths
        # ncurses package provides wide character version (libncursesw.a)
        ncurses = self.dependencies["ncurses"]
        cc = self.conf.get("tools.build:compiler_executables", {}).get("c", "cc")
        cflags = f"-I{ncurses.package_folder}/include -O2 -W -Wall"
        ldflags = f"-L{ncurses.package_folder}/lib -lncursesw"
        # Compile and link manually to ensure correct linking order (object before library)
        self.run(f"{cc} {cflags} -c -o {self.source_folder}/matroxset.o {self.source_folder}/matroxset.c", env="conanbuild")
        self.run(f"{cc} -o {self.source_folder}/matroxset {self.source_folder}/matroxset.o {ldflags}", env="conanbuild")

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "matroxset", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]