#!/usr/bin/env python3
"""Conan recipe for otp 1.2.2 - one-time pad / password list generator.

John Walker's "OTP" (fourmilab.ch/onetime) generates one-time pads or password
lists in several formats: fully random letters, digits, or word-like keys that
obey the digraph statistics of English.  For computer applications it can also
write a file with the MD5 signature of every generated key, so an application
can verify a key without storing it in plaintext.

OHOS notes
----------
* Pure C, three translation units (``otp.c``, ``md5.c``, ``random.c``), no
  third-party dependencies.  The upstream Makefile hardcodes ``CC = gcc``, so
  the OHOS compiler from ``tools.build:compiler_executables`` is passed on the
  make command line instead.
* Upstream ships a self-contained regression suite: ``make check`` runs
  ``test.sh`` (five ``./otp`` invocations with a fixed ``-R`` seed) and then
  ``diff test.mas test.out`` against a golden file.  The recipe runs exactly
  those steps (``sh test.sh`` + ``diff``); calling the script through ``sh``
  keeps it independent of the executable bit surviving archive extraction.
* CLI tool: installs ``bin/otp`` and the man page; a software-level
  ``commands.json`` is provided (L0k / R38).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class OtpConan(ConanFile):
    name = "otp"
    version = "1.2.2"
    description = "Generator for one-time pads or passwords"
    license = "Public Domain"
    homepage = "https://www.fourmilab.ch/onetime/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "otp OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        cc = self._compiler("c", "clang")
        opt = "-O2" if self.settings.build_type == "Release" else "-g -O0"
        apply_conandata_patches(self)
        # Upstream Makefile hardcodes `CC = gcc`; override on the command line.
        self.run('make -j1 CC="{}" CFLAGS="{} -Wall"'.format(cc, opt),
                 cwd=self.source_folder)
        # Upstream regression suite: five deterministic runs diffed against the
        # golden file test.mas.
        self.run("sh test.sh", cwd=self.source_folder)
        self.run("diff test.mas test.out", cwd=self.source_folder)

    def package(self):
        copy(self, "otp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "otp.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
