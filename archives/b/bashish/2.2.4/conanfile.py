#!/usr/bin/env python3
"""Conan recipe — bashish 2.2.4 (terminal theme engine).

Bashish is a theme environment for text terminals. It can change
colors, font, transparency and background image on a per-application
basis. Written in pure bash; built with autoconf
(./configure && make && make install).

Install layout:
  bin/bashish                     — main launcher
  share/bashish/                  — theme data (main/, themes/, lib/, …)
  share/man/man1/bashish.1       — man page

Run-time deps: bash >=2.04; optional: dialog (curses chooser),
xwininfo/xprop (X support).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, replace_in_file
from conan.tools.layout import basic_layout


class BashishConan(ConanFile):
    name = "bashish"
    version = "2.2.4"
    description = "Theme environment for text terminals (bash/zsh/tcsh)"
    license = "GPL-2.0"
    homepage = "https://bashish.sourceforge.net/"
    url = "https://sourceforge.net/projects/bashish/"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # bashish 2010 autoconf: config.status creates ./confXXXXXX
        # with umask 077 (0700 dir), but on setgid overlayfs the awk
        # subprocess cannot write subs1.awk → "Permission denied".
        # Fix: run configure (fails but generates config.status),
        # then sed umask 077 → umask 022 in config.status, rerun it.
        tc_args = [
            f"--prefix={self.package_folder}",
            "--datarootdir=${prefix}/share",
            "--bindir=${prefix}/bin",
        ]
        # configure generates config.status; expected to fail at
        # the awk step on restrictive filesystems.
        self.run(
            f"./configure {' '.join(tc_args)} || true",
            cwd=self.source_folder,
        )
        cs = os.path.join(self.source_folder, "config.status")
        if os.path.isfile(cs):
            replace_in_file(self, cs, "umask 077", "umask 022")
            self.run("sh config.status", cwd=self.source_folder)
        # make generates bashish headers + processed scripts.
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # `make install` honours DESTDIR for staging.
        self.run(
            f"make install DESTDIR={self.source_folder}/_staging",
            cwd=self.source_folder,
        )
        staging = os.path.join(self.source_folder, "_staging")
        # Copy staged tree into package_folder preserving layout.
        for root, _, files in os.walk(staging):
            rel = os.path.relpath(root, staging)
            dst_dir = os.path.join(self.package_folder, rel)
            os.makedirs(dst_dir, exist_ok=True)
            for f in files:
                shutil.copy2(os.path.join(root, f), os.path.join(dst_dir, f))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            self.buildenv_info.append_path("PATH", bin_dir)
