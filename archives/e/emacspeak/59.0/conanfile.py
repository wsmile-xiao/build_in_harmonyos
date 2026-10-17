#!/usr/bin/env python3
"""Conan recipe for emacspeak — Speech interface for Emacs.

Emacspeak is an Emacs Lisp extension package that provides a complete
audio desktop for visually impaired users. It consists of .el files,
Tcl/shell speech server scripts, and optional C++ TTS server modules.

This package installs the Lisp files and server scripts. Byte compilation
requires Emacs at build time and is skipped — .el files can be loaded
directly by Emacs at runtime.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class EmacspeakConan(ConanFile):
    name = "emacspeak"
    version = "59.0"
    description = "Speech interface for Emacs - auditory desktop for visually impaired users"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tvraman/emacspeak"
    url = ""

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # No compilation needed — emacspeak is an Emacs Lisp package.
        # Byte compilation requires Emacs runtime which is not available
        # at build time. The .el files can be loaded directly by Emacs.
        # The pre-generated emacspeak-loaddefs.el is included in the tarball.

    def package(self):
        # Install the entire emacspeak directory to share/emacspeak/
        copy(self, "*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "emacspeak"),
             excludes=".git*")

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = [os.path.join("share", "emacspeak")]
