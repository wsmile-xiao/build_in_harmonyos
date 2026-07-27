#!/usr/bin/env python3
"""Conan recipe for rig 1.11 — a program to generate fake identities.

rig generates random names, addresses, and phone numbers using data files.
It's a simple Makefile-based C++ project with no external dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RigConan(ConanFile):
    name = "rig"
    version = "1.11"
    description = "A program to generate fake identities (names, addresses, phone numbers)"
    license = "GPL-2.0-or-later"
    homepage = "https://rig.sourceforge.net/"
    url = ""  # CI fills this

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

        # R33: Get compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++")

        # Build flags from Conan settings
        cxxflags = []
        if self.settings.build_type == "Release":
            cxxflags.append("-O2")
        elif self.settings.build_type == "Debug":
            cxxflags.append("-g")
        cxxflags_str = " ".join(cxxflags)

        # Set DATADIR to package folder path so binary finds data at runtime
        datadir = os.path.join(self.package_folder, "share", "rig")

        # R9: Use -j1; run make in source folder (basic_layout puts build in subdir)
        self.run(f'make -C "{self.source_folder}" CXX="{cxx}" '
                 f'CXXFLAGS="{cxxflags_str}" DATADIR="{datadir}" -j1')

    def package(self):
        copy(self, "rig", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "*.idx", os.path.join(self.source_folder, "data"),
             os.path.join(self.package_folder, "share", "rig"))
        copy(self, "rig.6", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man6"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
