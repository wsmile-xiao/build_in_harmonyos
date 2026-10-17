#!/usr/bin/env python3
"""Conan recipe — smex 3.0 (Emacs Lisp M-x enhancement).

smex is a pure Emacs Lisp package (smex.el) that provides Ido-style
fuzzy matching for the Emacs M-x command interface. It has no build
system — the package simply installs smex.el into the Emacs site-lisp
directory.

Adaptation notes:
  - No configure/make/cmake; package() copies smex.el directly.
  - No compiled binaries; package_id clears OS/arch settings.
  - Runtime requires Emacs (not a Conan dependency; user-provided).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class SmexConan(ConanFile):
    name = "smex"
    version = "3.0"
    description = "M-x interface for Emacs with Ido-style fuzzy matching"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/nonsequitur/smex"
    url = "https://github.com/nonsequitur/smex"

    settings = "os", "arch"

    def package_id(self):
        # Pure Emacs Lisp file — identical on every OS/arch.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No build step — smex is a pure Emacs Lisp file.
        pass

    def package(self):
        # Install smex.el into share/emacs/site-lisp/.
        copy(
            self,
            "smex.el",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "emacs", "site-lisp"),
        )

    def package_info(self):
        # smex provides only an Emacs Lisp file; no libs or bins.
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share"]
