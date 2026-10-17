#!/usr/bin/env python3
"""Conan recipe for sic 1.3 - simple IRC client.

`sic` is an extremely small IRC client (about 250 lines of C): it reads
commands from standard input and multiplexes all channel traffic to standard
output.  It connects to a server (default irc.oftc.net:6667), sends the usual
NICK/USER registration, answers server PINGs and forwards PRIVMSGs.

OHOS notes
----------
* Single C source (``sic.c``) that #includes ``strlcpy.c`` and ``util.c``; it
  links against nothing but libc.  ``config.h`` is produced from the shipped
  ``config.def.h`` by the upstream Makefile.
* Upstream ships no tests; the consumer test in ``test_package`` really runs
  the installed binary: version/usage/connection-error paths plus a full IRC
  registration handshake against a local TCP server (and a PING/PONG exchange).
* CLI tool: installs ``bin/sic`` + man page; a software-level ``commands.json``
  is provided (L0k / R38).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class SicConan(ConanFile):
    name = "sic"
    version = "1.3"
    description = "Extremely simple IRC client"
    license = "MIT"
    homepage = "https://tools.suckless.org/sic/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sic OHOS adaptation is validated on Linux/OHOS, not "
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
        opt = "-O2" if self.settings.build_type == "Release" else "-g -O0"
        # Upstream Makefile: generates config.h from config.def.h, compiles
        # sic.c (which #includes strlcpy.c and util.c) and links bin/sic.
        self.run('make -j1 CC="{}" CFLAGS="{} -Wall"'.format(cc, opt),
                 cwd=self.source_folder)

    def package(self):
        copy(self, "sic", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "sic.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
