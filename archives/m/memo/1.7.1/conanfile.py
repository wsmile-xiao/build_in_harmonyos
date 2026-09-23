#!/usr/bin/env python3
"""Conan recipe for memo 1.7.1 - Unix-style note-taking tool.

``memo`` is a small POSIX command-line note-taking program: it appends notes
to ``.memo`` (path configurable via ``MEMO``/``~/.memorc``) and can list, view
and search them.  The whole program is a single C file (``memo.c``) built by a
hand-written Makefile.

OHOS notes
----------
* Plain Makefile project.  ``uname`` is not used; ``CC`` is injected from the
  Conan build environment and the extra flags are appended to ``CFLAGS``.
* The build environment has no ``install(1)``, so ``package()`` copies the
  binary and manual page manually.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class MemoConan(ConanFile):
    name = "memo"
    version = "1.7.1"
    description = "Unix-style note-taking software"
    license = "GPL-3.0-or-later"
    homepage = "https://www.nrosvall.name/memo/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "memo OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        cc = self._compiler("c", "clang")
        self.run('make CC="{}"'.format(cc), cwd=self.source_folder)

    def package(self):
        copy(self, "memo",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "memo.1",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
