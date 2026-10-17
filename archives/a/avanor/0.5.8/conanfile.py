#!/usr/bin/env python3
"""Conan recipe — avanor 0.5.8 (roguelike game, Makefile + ncurses).

Avanor is a terminal-based roguelike game. It uses a simple Makefile build
system and requires ncurses (wide char) for terminal UI.
"""

import os
import tarfile
from conan import ConanFile
from conan.tools.files import copy, download, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AvanorConan(ConanFile):
    name = "avanor"
    version = "0.5.8"
    description = "Avanor - The Land of Mystery, a roguelike game"
    license = "GPL-2.0-only"
    homepage = "http://www.avanor.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Source is a tar.bz2 file - download and extract manually
        url = self.conan_data["sources"]["url"]
        sha = self.conan_data["sources"]["sha256"]
        filename = "avanor-0.5.8-src.tar.bz2"
        download(self, url, filename, sha256=sha)
        with tarfile.open(filename, "r:bz2") as tf:
            tf.extractall(".")
        # Remove the archive after extraction
        os.unlink(filename)
        # Move contents from subdirectory to source folder (strip_root)
        extracted_dir = "avanor-0.5.8"
        if os.path.isdir(extracted_dir):
            for item in os.listdir(extracted_dir):
                os.rename(os.path.join(extracted_dir, item), item)
            os.rmdir(extracted_dir)

    def build(self):
        apply_conandata_patches(self)
        # avanor uses a plain Makefile (not autotools)
        # The Makefile uses g++ and needs ncurses includes
        # E293: Old C++98 code needs -Wno-error for C++17 compatibility
        ncurses_include = os.path.join(self.dependencies["ncurses"].package_folder, "include")
        ncurses_lib = os.path.join(self.dependencies["ncurses"].package_folder, "lib")

        cxxflags = ("-fsigned-char -pipe "
                    "-Wno-error=dynamic-exception-spec -Wno-error=register "
                    f"-I{ncurses_include} "
                    "-I./global -I./map -I./creature -I./engine -I./helpers "
                    "-I./item -I./magic -I./other -I./ -I./game")

        # Build with proper flags (use bfd linker to avoid lld libxml2 issue)
        self.run(f"make CC=\"{self.settings.compiler}++ -fuse-ld=bfd\" "
                 f"LD=\"{self.settings.compiler}++ -fuse-ld=bfd\" "
                 f"CFLAGS=\"{cxxflags}\" "
                 f"LIBS=\"-L{ncurses_lib} -lncursesw\" "
                 f"OPTFLAGS=\"-O2 -fPIC\"",
                 cwd=self.source_folder)

    def package(self):
        copy(self, "avanor", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "manual/*.html", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "avanor", "manual"))
        copy(self, "manual/*.css", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "avanor", "manual"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "gpl.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "changes.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "doc", "avanor"))
        # Copy data files needed at runtime
        copy(self, "manual/*.html", src=self.source_folder, dst=os.path.join(self.package_folder, "manual"))
        copy(self, "manual/*.css", src=self.source_folder, dst=os.path.join(self.package_folder, "manual"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Set TERMINFO for ncurses (only if ncurses is a dependency)
        if "ncurses" in self.dependencies:
            ncurses = self.dependencies["ncurses"]
            if ncurses.package_folder:
                terminfo = os.path.join(ncurses.package_folder, "share", "terminfo")
                self.runenv_info.define_path("TERMINFO", terminfo)
                self.runenv_info.define_path("TERMINFO_DIRS", terminfo)