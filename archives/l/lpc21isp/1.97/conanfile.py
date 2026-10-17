#!/usr/bin/env python3
"""Conan recipe — lpc21isp 1.97

Portable command line ISP (in-system programming) tool for NXP LPC1000/LPC2000
family and Analog Devices ADUC70xx microcontrollers. Flashes Intel HEX or
binary firmware over a serial port (RS232/COM).

Build system: plain Makefile (no configure, no `check`/`install` targets).
The upstream Makefile hard-codes `-static` for non-Apple platforms and uses
`OSTYPE`/`uname` for platform detection. On OHOS the platform branch falls
through to `COMPILE_FOR_LINUX` (termios serial path usable), but the hard-coded
`-static` would require libc.a. To stay consistent with other OHOS CLI tools in
this repo (dynamic link to musl) and keep the toolchain flags under Conan
control, this recipe compiles all four .c units directly (mirroring the official
Debian `rules` build line) instead of driving the upstream Makefile.

License: LGPL-3.0-or-later (README + lgpl-3.0.txt in source).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class Lpc21ispConan(ConanFile):
    name = "lpc21isp"
    version = "1.97"
    description = "Portable command line ISP tool for NXP LPC and ADI ADUC70xx microcontrollers — flashes firmware over serial"
    license = "LGPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/lpc21isp/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        pass

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        # Compile all four .c units and link in one step (Debian `rules` style).
        # Avoids the upstream Makefile's hard-coded `-static` (non-Apple branch)
        # so the binary dynamically links musl like other OHOS CLI tools.
        # R33: compiler comes from Conan conf (tools.build:compiler_executables),
        # never bare shell vars like `cc`/`${CC}` — on the release worker those
        # resolve to nothing. env="conanbuild" sources CC/CFLAGS/LDFLAGS from the
        # GnuToolchain env file so $CC / $CFLAGS expand correctly.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        sources = "lpc21isp.c adprog.c lpcprog.c lpcterm.c"
        self.run(
            f'"{cc}" -Wall {sources} -o lpc21isp',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        # lpc21isp is a command-line tool: install the binary to bin/
        copy(self, "lpc21isp", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
