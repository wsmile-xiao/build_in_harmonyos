#!/usr/bin/env python3
"""Conan recipe for perl-net-mpd (Net::MPD) — pure Perl module.

Net::MPD provides an object-oriented interface to communicate with an MPD
(Music Player Daemon) server. This is a pure Perl module using
Module::Build::Tiny as its build system.

Build steps: perl Build.PL → ./Build → ./Build install
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class PerlnetmpdConan(ConanFile):
    name = "perl-net-mpd"
    version = "0.07-r3"
    description = "Communicate with an MPD server"
    license = "MIT"
    homepage = "https://metacpan.org/pod/Net::MPD"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Pure Perl module — no C/C++ layout needed
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any (none for this module)
        apply_conandata_patches(self)
        # Module::Build::Tiny workflow
        self.run("perl Build.PL")
        self.run("./Build")

    def package(self):
        # Install to a temporary staging dir, then reorganize into lib/
        staging = os.path.join(self.package_folder, "_staging")
        self.run(f"./Build install --destdir {staging}")
        # Find the installed .pm files and copy them to lib/ at package root
        # so that G4 (product integrity check) can find standard lib/ directory
        pm_files = glob.glob(os.path.join(staging, "**", "Net", "MPD.pm"), recursive=True)
        if pm_files:
            # Determine the Perl lib root (parent of Net/)
            perl_lib_root = os.path.dirname(os.path.dirname(pm_files[0]))
            pkg_lib = os.path.join(self.package_folder, "lib")
            # Copy all files from perl_lib_root to pkg_lib preserving structure
            for root, dirs, files in os.walk(perl_lib_root):
                rel = os.path.relpath(root, perl_lib_root)
                dst = os.path.join(pkg_lib, rel) if rel != "." else pkg_lib
                os.makedirs(dst, exist_ok=True)
                for f in files:
                    shutil.copy2(os.path.join(root, f), os.path.join(dst, f))
        # Remove the temporary staging directory
        shutil.rmtree(staging, ignore_errors=True)

    def package_info(self):
        # Pure Perl module — no C/C++ libraries to link
        # R26 note: static linking not applicable (no native binaries)
        self.cpp_info.libs = []
        # Set PERL5LIB so consumers can find the Perl module
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            self.runenv_info.define_path("PERL5LIB", lib_dir)
