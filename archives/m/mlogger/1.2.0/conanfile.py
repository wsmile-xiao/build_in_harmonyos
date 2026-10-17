#!/usr/bin/env python3
"""Conan recipe — mlogger 1.2.0 (Makefile / single-file C CLI)

mlogger is a fork of bsdutils `logger` that logs arbitrary-length messages
(up to 64KB) to syslog via TCP/UDP/Unix-socket (nbrownus/mlogger).
Builds the single mlogger.c source into the `mlogger` executable.

Build system: plain Makefile (single `gcc -Wall -Wextra -O3 -o mlogger mlogger.c`
invocation), no configure, no install target.
License: BSD-4-Clause-UC (BSD-4-Clause-UC), derived from 4.3BSD logger.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MloggerConan(ConanFile):
    name = "mlogger"
    version = "1.2.0"
    description = "A simple utility that logs different sources to syslog (fork of bsdutils logger with 64KB line support)"
    license = "BSD-4-Clause-UC"
    homepage = "https://github.com/nbrownus/mlogger"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os 判断用 in 元组，不能 == "Linux"
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mlogger is adapted for Linux and OHOS only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: resolve the C compiler from Conan conf (never bare shell env vars
        #      like ${CC}/${CFLAGS}, which are empty on CI/release workers)
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp_execs.get("c") or "clang"
        # Faithful to upstream Makefile: cc -Wall -Wextra -O3 -o mlogger mlogger.c
        # No configure, no dependencies — single C file linking against libc.
        self.run(
            f"{cc} -Wall -Wextra -O3 -o mlogger mlogger.c",
            cwd=self.source_folder,
        )

    def package(self):
        # mlogger is a command-line tool: install the binary to bin/
        copy(
            self,
            "mlogger",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
