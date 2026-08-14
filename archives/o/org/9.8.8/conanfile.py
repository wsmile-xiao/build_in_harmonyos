#!/usr/bin/env python3
"""Conan recipe for GNU ELPA org 9.8.8."""

import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class OrgConan(ConanFile):
    name = "org"
    version = "9.8.8"
    description = "Outline-based notes management and organizer for GNU Emacs"
    license = "GPL-3.0-or-later"
    homepage = "https://orgmode.org"
    url = "https://orgmode.org"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def package_id(self):
        self.info.clear()

    def requirements(self):
        self.requires("emacs/29.1")

    def source(self):
        get(self, **self.conan_data["sources"])

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        # The GNU ELPA tarball ships generated org-loaddefs.el and
        # org-version.el, but no upstream test suite. Load the package with the
        # packaged source directory first in load-path to catch missing files.
        emacs = shlex.quote(os.environ.get("EMACS", "emacs"))
        source = shlex.quote(self.source_folder)
        expr = (
            "(progn "
            "(require 'org) "
            "(require 'ol) "
            "(unless (string= (org-version) \"9.8.8\") "
            "(error \"unexpected org-version: %S\" (org-version))) "
            "(unless (fboundp 'org-link-set-parameters) "
            "(error \"org-link-set-parameters missing\")))"
        )
        self.run(
            f"{emacs} -Q --batch -L {source} --eval {shlex.quote(expr)}",
            env="conanrun",
        )

    def package(self):
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"org-{self.version}",
        )
        copy(self, "*.el", self.source_folder, lisp_dir, keep_path=False)

        share_dir = os.path.join(self.package_folder, "share", "org")
        for pattern in ("README*", "CONTRIBUTE.org", "*.info"):
            copy(self, pattern, self.source_folder, share_dir, keep_path=False)
        copy(
            self,
            "*",
            os.path.join(self.source_folder, "etc"),
            os.path.join(share_dir, "etc"),
        )
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"org-{self.version}",
        )

        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

        self.buildenv_info.define_path("ORG_LISPDIR", lisp_dir)
        self.runenv_info.define_path("ORG_LISPDIR", lisp_dir)
        self.buildenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
        self.runenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
