#!/usr/bin/env python3
"""Conan recipe for libmoe 1.5.8 - multiple octets character encoding library.

libmoe handles multi-octet character encodings (ISO-2022-JP, EUC-JP, UTF-8,
Shift_JIS, ...) through a CES (character encoding scheme) abstraction and ships
the debugging front end ``mbconv``.

OHOS notes
----------
* The upstream Makefile hardcodes ``CC=gcc``, ``CPP=gcc -E``, ``LD=gcc``,
  ``AR=ar`` and installs into ``/usr/local``; the recipe compiles with the
  Conan C compiler (``llvm-ar``/``llvm-ranlib``) and installs explicitly.
* The build generates several headers from ``*.mk_btri.h`` inputs by piping
  them through the C preprocessor into the freshly built ``mk_btri`` helper
  (``$(CPP) ... | ./mk_btri > header``), so ``CPP`` must also be provided.
* ``mbconv`` is a CLI tool: a software level ``commands.json`` is provided
  (R38/L0k).  ``test_package`` drives the installed binary and checks the
  installed headers/library layout.
* Upstream's ``test.pl`` only prints CES boundary constants (no assertions), so
  the upstream step of R51 reports ``not_applicable`` and the harness performs
  the real verification.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# Headers installed by the upstream Makefile (INST=${Hs}).
_PUBLIC_HEADERS = (
    "mbversion.h", "mbcesdefs.h", "mbcesconf.h", "mblangconf.h",
    "altmalloc.h", "btri.h", "uirx.h", "wcrx.h", "mbces.h", "mb.h",
)


class LibmoeConan(ConanFile):
    name = "libmoe"
    version = "1.5.8"
    description = "C library to handle multiple octets character encoding, with the mbconv tool"
    license = "BSD-3-Clause"
    homepage = "http://pub.ks-and-ks.ne.jp/prog/libmoe/"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        compiler = self._compiler()
        arguments = [
            "-j1",
            "CC={}".format(compiler),
            "CPP=" + shlex.quote("{} -E".format(compiler)),
            "LD={}".format(compiler),
            "AR=llvm-ar",
            "RANLIB=llvm-ranlib",
            "CF=" + shlex.quote("-O2 -Wall -fpic -fgnu89-inline -I."),
        ]
        # `all` builds libmoe.a, mbconv and the man page; the shared library is
        # a separate target.
        self.run("make " + " ".join(arguments) + " all", cwd=self.source_folder)
        if self.options.shared:
            self.run("make " + " ".join(arguments) + " libmoe.so", cwd=self.source_folder)

    def package(self):
        package_folder = self.package_folder
        compiler = self._compiler()
        arguments = [
            "-j1",
            "CC={}".format(compiler),
            "CPP=" + shlex.quote("{} -E".format(compiler)),
            "LD={}".format(compiler),
            "AR=llvm-ar",
            "RANLIB=llvm-ranlib",
            "CF=" + shlex.quote("-O2 -Wall -fpic -fgnu89-inline -I."),
            "PREFIX={}".format(package_folder),
            "INCDIR={}".format(os.path.join(package_folder, "include", "moe")),
            "LIBADIR={}".format(os.path.join(package_folder, "lib")),
            "LIBSODIR={}".format(os.path.join(package_folder, "lib")),
            "BINDIR={}".format(os.path.join(package_folder, "bin")),
            "LIBEXECDIR={}".format(os.path.join(package_folder, "libexec", "moe")),
            "MANDIR={}".format(os.path.join(package_folder, "share", "man")),
        ]
        self.run("make " + " ".join(arguments) + " install", cwd=self.source_folder)
        for header in _PUBLIC_HEADERS:
            source = os.path.join(self.source_folder, header)
            if os.path.isfile(source):
                copy(self, header, src=self.source_folder,
                     dst=os.path.join(package_folder, "include", "moe"))
        copy(self, "libmoe.shtml", src=self.source_folder,
             dst=os.path.join(package_folder, "licenses"), keep_path=False)
        if not self.options.shared:
            # The upstream install rule always ships the shared library; drop it
            # (plus its version symlinks) when the consumer asked for static.
            for name in os.listdir(os.path.join(package_folder, "lib")):
                if name.startswith("libmoe.so"):
                    os.remove(os.path.join(package_folder, "lib", name))

    def package_info(self):
        self.cpp_info.libs = ["moe"]
        self.cpp_info.includedirs = ["include", "include/moe"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libmoe")
        self.cpp_info.set_property("cmake_target_name", "libmoe::libmoe")
        self.cpp_info.set_property("pkg_config_name", "libmoe")
