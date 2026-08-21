#!/usr/bin/env python3
"""Conan recipe for away 0.9.5 on HarmonyOS PC.

away is a terminal locking program (Terminal locking program): locks
the terminal, checks for new mail and shows an away message in `w`.
It uses PAM to lock the terminal (like xlock). Pure C (~690 lines),
built with its Makefile.

Dependency: linux-pam/1.7.2 (libpam + libpam_misc, published on ohpcd).
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class AwayConan(ConanFile):
    name = "away"
    version = "0.9.5"
    package_type = "application"
    license = "GPL-2.0"
    homepage = "https://web.archive.org/web/20050316212734/http://unbeatenpath.net/software/away/"
    url = "https://salsa.debian.org/debian/away"
    description = ("Terminal locking program (PAM-based, shows away "
                   "message in `w`)")
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("linux-pam/1.7.2")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def build(self):
        pam = self.dependencies["linux-pam"]
        # Makefile: CC=gcc, CFLAGS=-O2 -Wall -D_REENTRANT,
        # LIBS=-lpthread -lpam -lpam_misc —— 覆盖为 clang 绝对路径 +
        # linux-pam 头/库路径（make 命令行变量优先级最高）
        self.run(
            "make "
            "CC=/data/service/hnp/bin/clang "
            f"CFLAGS='-O2 -Wall -D_REENTRANT "
            f"-I{pam.package_folder}/include' "
            f"LIBS='-L{pam.package_folder}/lib -lpthread -lpam -lpam_misc'",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "away", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "away.pam", src=os.path.join(self.source_folder, "data"),
             dst=os.path.join(self.package_folder, "etc", "pam.d"))
        copy(self, "away.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.conf_info.define("user.away:exe", os.path.join(
            self.package_folder, "bin", "away"))
