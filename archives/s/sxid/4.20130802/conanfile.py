#!/usr/bin/env python3
"""Conan recipe for sxid 4.20130802 - s[ug]id file and directory checker.

sXid audits setuid/setgid files and directories: it walks the configured search
paths, records owner/group/mode, tracks directories by inode and regular files
by SHA-256, and reports additions / removals / changes since the previous run.

Upstream ships an autotools project (autoconf 2.69, pre-generated ``configure``)
but no test suite.  This recipe compiles the six C sources directly with the
OHOS clang and generates the small ``src/config.h`` that ``configure`` would
normally emit (VERSION / CONF_FILE / MAIL_PROG / CL_SUBJ / HAVE_STRTOK_R).  That
keeps the build deterministic and avoids the whole autoreconf / automake /
config.guess surface.  OHOS bionic provides ``getopt_long_only``, so the
bundled GNU getopt sources are not compiled.

The program needs no third-party library.  It is a CLI tool, so a software
level ``commands.json`` is provided (L0k).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

_SOURCES = ("conffile.c", "logging.c", "notify.c", "search.c", "sha2.c", "sxid.c")

_CONFIG_H = """\
#define VERSION "4.20130802"
#define CONF_FILE "/etc/sxid.conf"
#define MAIL_PROG "/usr/bin/mail"
#define CL_SUBJ 1
#define HAVE_STRTOK_R 1
"""


class SxidConan(ConanFile):
    name = "sxid"
    version = "4.20130802"
    description = "s[ug]id file and directory checker (setuid/setgid audit + SHA-256 tracking)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/taem/sxid"
    url = "https://github.com/taem/sxid"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sxid OHOS adaptation is validated on Linux/OHOS, not "
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

    def _generate_config_h(self):
        # config.h is produced by configure upstream; generate the five macros
        # the sources actually consume.  Written next to the sources so that
        # sxid.h's ``#include "config.h"`` resolves.
        target = os.path.join(self.source_folder, "src", "config.h")
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_CONFIG_H)

    def build(self):
        apply_conandata_patches(self)
        self._generate_config_h()
        src = os.path.join(self.source_folder, "src")
        binary = os.path.join(self.build_folder, "sxid")
        opt = "-O2" if self.settings.build_type == "Release" else "-g -O0"
        sources = " ".join('"%s"' % os.path.join(src, name) for name in _SOURCES)
        self.run('"{}" {} -std=gnu99 -Wall -o "{}" {}'.format(
            self._compiler("c", "clang"), opt, binary, sources))
        # Compile-evidence smoke run; upstream ships no test suite.
        self.run('"{}" -V'.format(binary))

    def package(self):
        copy(self, "sxid", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "sxid.1.in", src=os.path.join(self.source_folder, "docs"),
             dst=man_dir, keep_path=False)
        man = os.path.join(man_dir, "sxid.1.in")
        if os.path.isfile(man):
            replace_in_file(self, man, "@TMPCONF@", "/etc")
            os.rename(man, os.path.join(man_dir, "sxid.1"))
        share = os.path.join(self.package_folder, "share", "sxid")
        copy(self, "sxid.conf", src=os.path.join(self.source_folder, "examples"),
             dst=share, keep_path=False)
        copy(self, "sxid.cron", src=os.path.join(self.source_folder, "examples"),
             dst=share, keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "sxid")
        self.cpp_info.set_property("cmake_target_name", "sxid::sxid")
