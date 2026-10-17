#!/usr/bin/env python3
"""Conan recipe for mailcheck 1.91.2.

mailcheck is a small command-line utility that checks multiple mailboxes
(mbox, Maildir, POP3, IMAP) for new mail. It uses a plain Makefile
(no configure script) and produces a single binary: mailcheck.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MailcheckConan(ConanFile):
    name = "mailcheck"
    version = "1.91.2"
    description = "Check multiple mailboxes and/or Maildirs for new mail"
    license = "GPL-2.0-or-later"
    homepage = "https://mailcheck.sourceforge.net/"
    url = "https://mailcheck.sourceforge.net/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: Get compiler from Conan conf, not shell env vars
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp_execs.get("c")
        if not cc:
            if cross_building(self):
                raise ConanInvalidConfiguration(
                    "cross builds require tools.build:compiler_executables[c]"
                )
            cc = "cc"
        # Plain Makefile build — no configure step needed.
        # The Makefile hardcodes -Wall -O2 and -s (strip); CC is the only
        # variable it references, so a single CC override suffices (R1).
        self.run(f'make CC="{cc}" -j1', cwd=self.source_folder, env=["conanbuild"])

    def package(self):
        copy(
            self, "COPYING", self.source_folder,
            os.path.join(self.package_folder, "licenses"), keep_path=False,
        )
        copy(
            self, "mailcheck", self.source_folder,
            os.path.join(self.package_folder, "bin"), keep_path=False,
        )
        copy(
            self, "mailcheck.1", self.source_folder,
            os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self, "mailcheckrc", self.source_folder,
            os.path.join(self.package_folder, "etc"), keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
