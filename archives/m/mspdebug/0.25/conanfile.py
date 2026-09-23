#!/usr/bin/env python3
"""Conan recipe — mspdebug 0.25

MSPDebug: a debugger/programmer for MSP430 MCUs (drivers for TI FET,
BSL, FTDI/CP210x/TI3410 USB adapters, plus a built-in simulator).
Build system: plain Makefile; links against the libusb-0.1 legacy API
(provided by libusb-compat on top of libusb/1.x) and optionally readline
(disabled here — OHOS ships no readline).
License: GPL-2.0-or-later (BSD-3-Clause for sim1x bits).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

CC_FALLBACK = "/data/service/hnp/bin/clang"


class MspdebugConan(ConanFile):
    name = "mspdebug"
    version = "0.25"
    description = ("mspdebug: debugger and programmer for MSP430 MCUs "
                   "(TI FET/BSL drivers, gdb remote, built-in simulator)")
    license = "GPL-2.0-or-later"
    homepage = "https://dlbeer.co.nz/mspdebug/"
    url = "https://github.com/dlbeer/mspdebug"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # mspdebug links the libusb-0.1 legacy API (usb.h / -lusb);
        # libusb-compat provides it on top of libusb/1.x.  libusb is pinned
        # directly as well so both package folders are addressable below.
        self.requires("libusb-compat/0.1.7")
        self.requires("libusb/1.0.27")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        compilers = self.conf.get("tools.build:compiler_executables") or {}
        self._cc = compilers.get("c", CC_FALLBACK)
        self._inc, self._lib = [], []
        for name in ("libusb-compat", "libusb"):
            dep = self.dependencies[name]
            self._inc += [os.path.join(dep.package_folder, d)
                          for d in dep.cpp_info.includedirs]
            self._lib += [os.path.join(dep.package_folder, d)
                          for d in dep.cpp_info.libdirs]

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # E386 pattern: start from the healthy worktree cwd and let the shell
        # cd internally (the conan cache build dir trips HMDFS getcwd()).
        # WITHOUT_READLINE: OHOS ships no readline (console input fallback);
        # INSTALL=install: the Makefile hardcodes /usr/bin/install.
        inc = " ".join(f"-I{d}" for d in self._inc)
        lib = " ".join(f"-L{d}" for d in self._lib)
        # Keep the full variable set in both invocations: `make install`
        # re-evaluates the default goal and would otherwise fall back to
        # gcc (absent on OHOS) and rebuild objects without the include paths.
        self._make_vars = (
            f'WITHOUT_READLINE=1 CC="{self._cc}" INSTALL=install PREFIX=/ '
            f'CFLAGS="{inc}" '
            f'MSPDEBUG_LIBS="{lib} -lusb -lusb-1.0 -lpthread -ldl"')
        self.run(
            f'cd "{src}" && make -j1 {self._make_vars}',
            env="conanbuild")

    def package(self):
        src = self.source_folder
        self.run(
            f'cd "{src}" && make install {self._make_vars} '
            f'DESTDIR="{self.package_folder}"',
            env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
