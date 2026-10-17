#!/usr/bin/env python3
"""Conan recipe for nyancat 1.5.2 — Terminal Nyancat on HarmonyOS PC.

nyancat renders the classic "rainbow cat" animation in a terminal (standalone
or as an inetd-style telnet server). Pure POSIX C99, zero external
dependencies: libc only (stdio/unistd/getopt/ioctl/signal). No pkg-config,
no external libraries, no build-system configure stage.

Key adaptation points:
  - Build system is a plain two-level Makefile (top + src/), every variable
    uses `?=` so CC is overridable from the command line — no patching needed.
    (Unlike Autotools projects: there is no configure, hence no autoreconf,
    no E0111 umask-077 issue, no config.status temp-dir issue.)
  - R33: CC comes from Conan conf, never from shell env vars.
  - R9: make -j1 (HMDFS jobserver quirks; single C file, negligible cost).
  - telnet mode is a pure-stdio protocol parser (read/write on fd 0, inetd
    style) — no socket/bind/listen calls, no network libraries required.
  - telnet.h defines an `ECHO` macro that shadows stdio's ECHO flag; the
    upstream code already `#undef`s it after including termios.h — no fix-up
    needed on OHOS.
  - package(): only the binary is installed. The upstream `install` target
    hardcodes /usr/bin and /usr/share/man (no DESTDIR support) and the
    systemd units are meaningless on OHOS PC (no systemd), so manual copy
    is used (netris precedent).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NyancatConan(ConanFile):
    name = "nyancat"
    version = "1.5.2"
    description = "Terminal Nyancat — renders the rainbow cat in a terminal (standalone / telnet)"
    license = "NCSA"
    homepage = "https://github.com/klange/nyancat"
    url = ""  # CI fills this
    topics = ("terminal", "animation", "telnet", "toy")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # None. Verified by inventorying every #include in src/nyancat.c:
        # ctype/stdio/stdint/string/stdlib/unistd/signal/time/setjmp/getopt/
        # sys/ioctl/termios — all libc. Upstream deliberately avoids libm
        # ("I refuse to include libm to keep this low", src/nyancat.c:140).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # The tarball ships no stale build artifacts (14 files, no .o), so no
        # make clean is required; guard anyway for reproducible rebuilds.
        self.run("make clean", cwd=self.source_folder)
        # R33: CC from Conan conf, never from shell env (empty on CI workers).
        # conf is registered as a dict (tools.build:compiler_executables={'c': ...});
        # read it the same way as the sl recipe (sub-key str lookup fails here).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # Upstream Makefile already defaults CFLAGS to -g -Wall -Wextra
        # -std=c99 -pedantic -Wwrite-strings; keep them (they pass on OHOS
        # clang) and only inject CC. make -j1 per R9.
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Upstream `install` target hardcodes /usr/bin + /usr/share/man
        # (no DESTDIR); OHOS PC has no systemd, so the systemd/ units are
        # intentionally not packaged. Binary only (netris precedent).
        copy(self, "nyancat", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
