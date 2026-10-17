#!/usr/bin/env python3
"""Conan 2.x recipe — radioclk 1.0.pristine (radioclkd ntp refclock daemon).

radioclkd decodes the DCF77/MSF/WWVB radio time signal from a receiver
wired to a serial-port modem-status line (DCD/CTS/DSR) and publishes the
decoded time to ntpd through the SHM reference-clock driver (SysV shared
memory segment).

Source: the upstream author site (buzzard.org.uk) is long parked; the
authoritative pristine 1.0 tarball is mirrored in the Debian pool as
radioclk_1.0.pristine.orig.tar.gz (same bytes Debian ships, no Debian
patches applied here). Repo precedent: cgvg/unzoo/libbrahe & friends.

Build: single C translation unit (radioclkd.c); upstream Makefile only
links radioclkd and its install target assumes /usr/bin/install plus an
/sbin layout, so this recipe drives the compile target of the Makefile
and installs the binary itself. refclock_shm.c is a drop-in replacement
file for the ntp distribution and is intentionally NOT built.

Portability (applied in source(), recorded in manifest):
  1) <termio.h> replaced by <termios.h> + <sys/ioctl.h> — the legacy
     glibc header is absent from musl, and upstream relied on the glibc
     header chain for the TIOCM_* modem-line macros and the ioctl()
     prototype (musl keeps them in <termios.h>).
  2) TIOCMIWAIT fallback #define — the ioctl number is x86-side and is
     not defined by asm-generic/musl headers used on aarch64. Where the
     kernel serial driver rejects the ioctl, WaitOnSerialChange()
     returns -1 and the documented `-p` polling mode is the runtime
     fallback (see upstream README).
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class RadioclkConan(ConanFile):
    name = "radioclk"
    version = "1.0.pristine"
    description = (
        "radioclkd: simple ntp refclock daemon decoding DCF77/MSF/WWVB "
        "radio time signals from a serial-port receiver"
    )
    license = "GPL-2.0-or-later"
    homepage = "http://www.buzzard.org.uk/jonathan/radioclock.html"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # no patch files; portability edits happen in source() below
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        # Pure C89 daemon: C++ settings are meaningless
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "radioclk/1.0.pristine is prepared for Linux/OHOS"
            )

    def requirements(self):
        # libc only: termios ioctls, SysV shm, syslog — all in musl
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        radioclkd_c = os.path.join(self.source_folder, "radioclkd.c")

        # (1) legacy <termio.h> does not exist in musl. Upstream relied on
        #     the glibc header chain to pull in the modem-line ioctl macros
        #     and the ioctl() prototype; musl keeps TIOCM_*/TIOCMGET/... in
        #     <termios.h>, so include that (plus <sys/ioctl.h> for ioctl)
        #     explicitly.
        replace_in_file(
            self, radioclkd_c,
            "#include<termio.h>\n",
            "#include<termios.h>\n"
            "#include<sys/ioctl.h>\n",
        )

        # (2) TIOCMIWAIT is not defined by asm-generic/musl headers
        #     (aarch64); provide the historical Linux ioctl number so the
        #     daemon compiles. Runtime fallback: -p polling mode.
        replace_in_file(
            self, radioclkd_c,
            "#include<setjmp.h>\n",
            "#include<setjmp.h>\n"
            "\n"
            "/*\n"
            " * Portability: musl/OHOS does not ship the legacy\n"
            " * <termio.h> header (it was included but never used).\n"
            " * TIOCMIWAIT is an x86-side ioctl number that the\n"
            " * asm-generic (aarch64/musl) headers do not define;\n"
            " * provide the historical Linux value so the daemon still\n"
            " * compiles. On kernels whose serial driver rejects the\n"
            " * ioctl, WaitOnSerialChange() returns -1 and the\n"
            " * documented `-p` polling mode is the runtime fallback.\n"
            " */\n"
            "#ifndef TIOCMIWAIT\n"
            "#define TIOCMIWAIT 0x5452\n"
            "#endif\n",
        )

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)  # no-op: no patch files
        # Upstream Makefile assigns CC with `=` (overridable on the
        # command line). Only the radioclkd compile+link target is used;
        # the install target (hardcoded /usr/bin/install, /sbin layout)
        # is replaced by package() below.
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # R9: always -j1 for old single-file make projects
        self.run(f'make -j1 radioclkd CC="{cc}"',
                 cwd=self.source_folder, env="conanbuild")
        binary = os.path.join(self.source_folder, "radioclkd")
        if not os.path.isfile(binary):
            raise ConanException("radioclkd binary was not produced")

    def package(self):
        copy(self, "radioclkd",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "radioclk", "doc"))
        copy(self, "ChangeLog",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "radioclk", "doc"))
        copy(self, "radioclkd.1",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        if not os.path.isfile(os.path.join(self.package_folder, "bin",
                                           "radioclkd")):
            raise ConanException("packaged radioclkd binary missing")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
