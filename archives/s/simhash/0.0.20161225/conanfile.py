#!/usr/bin/env python3
"""Conan recipe for simhash 0.0.20161225 - file similarity hash tool.

simhash (Bart Massey) computes similarity hashes for files and compares them:
similar documents produce matching hash bits, so the tool can rank near
duplicates without reading the files again.

It is a small C program (``simhash.c``, ``hash.c``, ``heap.c``, ``crc32.c``)
built by a plain Makefile that hardcodes ``CC=gcc`` and ``-O4 -ansi -pedantic``
(neither ``gcc`` nor ``-O4``/``-ansi`` is appropriate for the OHOS clang
toolchain), so ``build()`` compiles the four translation units directly with
the Conan compiler and ``-lm``.

OHOS notes
----------
* The upstream Makefile's ``install`` target writes to ``/usr/local``; the
  recipe installs ``bin/simhash``, ``share/man/man1/simhash.1`` and the license
  itself instead.
* CLI tool: a software level ``commands.json`` is provided (R38/L0k).
* ``test_package`` drives the installed binary through a Python harness:
  identical files must compare to ``1.0``, a one word edit to a positive
  score and unrelated content to ``.00``.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

_SOURCES = ("simhash.c", "crc32.c", "heap.c", "hash.c")


class SimhashConan(ConanFile):
    name = "simhash"
    version = "0.0.20161225"
    description = "File similarity hash tool (simhash for near-duplicate detection)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/BartMassey/simhash"
    url = ""

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = executables.get("c") or "clang"
        if not compiler:
            raise ConanInvalidConfiguration("no C compiler configured")
        return compiler

    def build(self):
        binary = os.path.join(self.build_folder, "simhash")
        sources = " ".join(
            '"{}"'.format(os.path.join(self.source_folder, name)) for name in _SOURCES)
        self.run('"{}" -O3 -Wall -o "{}" {} -lm'.format(self._compiler(), binary, sources))

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "simhash", src=self.build_folder, dst=bin_dir, keep_path=False)
        os.chmod(os.path.join(bin_dir, "simhash"), 0o755)
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "simhash.man", src=self.source_folder, dst=man_dir, keep_path=False)
        os.rename(os.path.join(man_dir, "simhash.man"),
                  os.path.join(man_dir, "simhash.1"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
