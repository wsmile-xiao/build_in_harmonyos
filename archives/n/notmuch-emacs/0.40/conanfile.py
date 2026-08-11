#!/usr/bin/env python3
"""Conan recipe for the Notmuch Emacs Lisp front-end 0.40."""

import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class NotmuchEmacsConan(ConanFile):
    name = "notmuch-emacs"
    version = "0.40"
    description = "Emacs Lisp front-end for Notmuch mail"
    license = "GPL-3.0-or-later"
    homepage = "https://notmuchmail.org"
    url = "https://notmuchmail.org"
    package_type = "unknown"

    settings = "os", "arch"

    _emacs_sources = (
        "notmuch-lib.el",
        "notmuch-compat.el",
        "notmuch-parser.el",
        "notmuch.el",
        "notmuch-query.el",
        "notmuch-show.el",
        "notmuch-tree.el",
        "notmuch-wash.el",
        "notmuch-hello.el",
        "notmuch-mua.el",
        "notmuch-address.el",
        "notmuch-maildir-fcc.el",
        "notmuch-message.el",
        "notmuch-crypto.el",
        "notmuch-tag.el",
        "coolj.el",
        "notmuch-print.el",
        "notmuch-version.el",
        "notmuch-jump.el",
        "notmuch-company.el",
        "notmuch-draft.el",
    )

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
        self._generate_version_files()
        self._run_emacs_autoloads()
        self._run_emacs_batch_smoke()
        self._run_emacs_byte_compile()

    def _emacs_dir(self):
        return os.path.join(self.source_folder, "emacs")

    def _generate_version_files(self):
        emacs_dir = self._emacs_dir()
        generated = "Generated file (from Conan recipe) -- do not edit!"
        save(
            self,
            os.path.join(emacs_dir, "notmuch-version.el"),
            "\n".join(
                [
                    ";;; notmuch-version.el --- version of notmuch  -*- emacs-lisp -*-",
                    f";; {generated}",
                    "",
                    ";;; Code:",
                    "",
                    f"(defconst notmuch-emacs-version \"{self.version}\"",
                    "  \"Version of Notmuch Emacs MUA.\")",
                    "",
                    "(provide 'notmuch-version)",
                    "",
                    ";;; notmuch-version.el ends here",
                    "",
                ]
            ),
        )
        save(
            self,
            os.path.join(emacs_dir, "notmuch-pkg.el"),
            "\n".join(
                [
                    f";; {generated}",
                    "(define-package",
                    "  \"notmuch\"",
                    f"  \"{self.version}\"",
                    "  \"Emacs based front-end (MUA) for notmuch\"",
                    "  '((emacs \"25.1\")))",
                    "",
                ]
            ),
        )

    def _emacs(self):
        return shlex.quote(os.environ.get("EMACS", "emacs"))

    def _run_emacs_autoloads(self):
        emacs_dir = self._emacs_dir()
        sources = " ".join(
            shlex.quote(os.path.join(emacs_dir, name)) for name in self._emacs_sources
        )
        autoloads = shlex.quote(os.path.join(emacs_dir, "notmuch-autoloads.el"))
        self.run(
            f"{self._emacs()} -Q --batch -L {shlex.quote(emacs_dir)} "
            f"-l autoloads-gen.el -f autoloads-gen-batch {autoloads} {sources}",
            cwd=emacs_dir,
            env="conanrun",
        )

    def _run_emacs_batch_smoke(self):
        emacs_dir = shlex.quote(self._emacs_dir())
        expr = (
            "(progn "
            "(require 'notmuch-version) "
            "(require 'notmuch-lib) "
            "(require 'notmuch) "
            f"(unless (string= notmuch-emacs-version \"{self.version}\") "
            "(error \"unexpected notmuch-emacs-version: %S\" notmuch-emacs-version)) "
            "(unless (fboundp 'notmuch-search) "
            "(error \"notmuch-search missing\")))"
        )
        self.run(
            f"{self._emacs()} -Q --batch -L {emacs_dir} --eval {shlex.quote(expr)}",
            env="conanrun",
        )

    def _run_emacs_byte_compile(self):
        emacs_dir = self._emacs_dir()
        for source in self._emacs_sources:
            self.run(
                f"{self._emacs()} -Q --batch -L {shlex.quote(emacs_dir)} "
                f"-f batch-byte-compile {shlex.quote(os.path.join(emacs_dir, source))}",
                env="conanrun",
            )

    def package(self):
        emacs_dir = self._emacs_dir()
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"notmuch-{self.version}",
        )
        for pattern in ("*.el", "*.elc"):
            copy(self, pattern, emacs_dir, lisp_dir, keep_path=False)

        share_dir = os.path.join(self.package_folder, "share", "notmuch-emacs")
        for pattern in ("notmuch-logo.svg", "notmuch-emacs-mua", "notmuch-emacs-mua.desktop"):
            copy(self, pattern, emacs_dir, share_dir, keep_path=False)
        for pattern in ("README*", "NEWS", "AUTHORS"):
            copy(self, pattern, self.source_folder, share_dir, keep_path=False)
        copy(
            self,
            "COPYING*",
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
            f"notmuch-{self.version}",
        )

        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []

        self.buildenv_info.define_path("NOTMUCH_EMACS_LISPDIR", lisp_dir)
        self.runenv_info.define_path("NOTMUCH_EMACS_LISPDIR", lisp_dir)
        self.buildenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
        self.runenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
