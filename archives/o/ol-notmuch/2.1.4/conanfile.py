#!/usr/bin/env python3
"""Conan recipe for ol-notmuch 2.1.4."""
import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class OlNotmuchConan(ConanFile):
    name = "ol-notmuch"
    version = "2.1.4"
    description = "Org mode links to Notmuch buffers"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/tarsius/ol-notmuch"
    url = ""
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def package_id(self):
        self.info.clear()

    def requirements(self):
        self.requires("emacs/29.1")
        self.requires("compat/31.0.0.2")
        self.requires("org/9.8.8")
        self.requires("notmuch-emacs/0.40")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        make = shlex.quote(self.conf.get("tools.gnu:make_program", default="make"))
        command = (
            f"{make} lisp "
            f"EMACS={self._emacs()} "
            f"LOAD_PATH={shlex.quote(self._make_load_path())}"
        )
        self.run(command, cwd=self.source_folder, env=["conanbuild", "conanrun"])

    def _emacs(self):
        return shlex.quote(os.environ.get("EMACS", "emacs"))

    def _make_load_path(self):
        paths = [
            os.path.join(
                self.dependencies["compat"].package_folder,
                "share",
                "emacs",
                "site-lisp",
                "compat-31.0.0.2",
            ),
            os.path.join(
                self.dependencies["org"].package_folder,
                "share",
                "emacs",
                "site-lisp",
                "org-9.8.8",
            ),
            os.path.join(
                self.dependencies["notmuch-emacs"].package_folder,
                "share",
                "emacs",
                "site-lisp",
                "notmuch-0.40",
            ),
        ]
        paths.append(self.source_folder)
        return " ".join(f"-L {shlex.quote(path)}" for path in paths)

    def package(self):
        share = os.path.join(self.package_folder, "share", "ol-notmuch")
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"ol-notmuch-{self.version}",
        )
        for pattern in ("ol-notmuch.el", "ol-notmuch.elc", "ol-notmuch-autoloads.el"):
            copy(self, pattern, self.source_folder, lisp_dir, keep_path=False)
        copy(self, "Makefile", self.source_folder, share)
        copy(self, "README.org", self.source_folder, share)
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        root = os.path.join(self.package_folder, "share", "ol-notmuch")
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"ol-notmuch-{self.version}",
        )
        self.buildenv_info.define_path("OL_NOTMUCH_ROOT", root)
        self.runenv_info.define_path("OL_NOTMUCH_ROOT", root)
        self.buildenv_info.define_path("OL_NOTMUCH_LISPDIR", lisp_dir)
        self.runenv_info.define_path("OL_NOTMUCH_LISPDIR", lisp_dir)
        self.buildenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
        self.runenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
