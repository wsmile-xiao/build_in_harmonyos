#!/usr/bin/env python3
"""Conan recipe for delight 1.7."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class DelightConan(ConanFile):
    name = "delight"
    version = "1.7"
    description = "A dimmer switch for your lighter text (Emacs mode line name customisation)"
    license = "GPL-3.0-or-later"
    homepage = "https://savannah.nongnu.org/projects/delight"
    url = ""
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"delight supports Linux and OHOS, got {self.settings.os}"
            )

    def package_id(self):
        self.info.clear()

    def requirements(self):
        # cl-lib and nadvice (Package-Requires) are built into Emacs 24.3+.
        self.requires("emacs/29.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _emacs(self):
        dependency = self.dependencies["emacs"]
        emacs = os.path.join(dependency.package_folder, "bin", "emacs")
        if not os.path.isfile(emacs):
            raise ConanInvalidConfiguration(f"Emacs executable is missing: {emacs}")
        return shlex.quote(emacs)

    def build(self):
        # delight 1.7 ships no upstream test suite (the ELPA tarball contains
        # only delight.el, delight-pkg.el and COPYING).  Upstream validation is
        # therefore Emacs batch byte-compilation followed by a batch load of
        # the compiled library, the same approach used by the repository's
        # other Emacs Lisp packages.
        source = os.path.join(self.source_folder, "delight.el")
        compiled = os.path.join(self.source_folder, "delight.elc")
        self.run(
            f"{self._emacs()} -Q --batch -f batch-byte-compile {shlex.quote(source)}",
            cwd=self.source_folder,
            env="conanbuild",
        )
        if not os.path.isfile(compiled) or os.path.getsize(compiled) == 0:
            raise ConanException("delight.elc was not produced")
        load_check = (
            "(unless (featurep 'delight) (error \"delight feature was not provided\"))"
        )
        self.run(
            f"{self._emacs()} -Q --batch -l {shlex.quote(compiled)} "
            f"--eval {shlex.quote(load_check)}",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def _lisp_dir(self):
        return os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"delight-{self.version}",
        )

    def package(self):
        lisp_dir = self._lisp_dir()
        copy(self, "delight.el", self.source_folder, lisp_dir)
        copy(self, "delight.elc", self.source_folder, lisp_dir)
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        lisp_dir = self._lisp_dir()
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        self.buildenv_info.define_path("DELIGHT_LISPDIR", lisp_dir)
        self.runenv_info.define_path("DELIGHT_LISPDIR", lisp_dir)
        self.buildenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
        self.runenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
