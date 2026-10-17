#!/usr/bin/env python3
"""Conan recipe — pconsole 1.2.0

Parallel console: one keyboard, many terminals.  pconsole attaches to a set
of tty devices and injects every keystroke into all of them, so a single
typed command reaches every attached machine at once.

Build system: Autotools, but a hand-written autoconf-2.13 `configure` plus a
hand-written `Makefile.in` (no automake, no config.guess/config.sub).
License: GPL-2.0-or-later (the tarball ships the GPL text as `GPL`).

Three upstream traits shape this recipe:

1. `Makefile.in` has no VPATH support at all (a `.c.o:` suffix rule with
   `-I.` / `-Iinclude` relative to the *build* directory and no `$(srcdir)`),
   so the only workable layout is an in-tree build.
2. The `install` target ignores `DESTDIR` and installs into the absolute
   `$(bindir)`.  Pointing `--prefix` at the package folder therefore stages
   the package in place, with the correct absolute paths baked into the
   generated `pconsole.sh`.
3. `seteuid()` is called unconditionally at all three of its call sites --
   twice inside `put_conn()` (`seteuid(0)` to regain root privs and
   `seteuid(getuid())` to drop them again, bracketing the `ioctl(TIOCSTI)` of
   every injected keystroke) and once in `main()` at startup.  All three are
   fatal on OpenHarmony/HarmonyOS (uncatchable SIGSYS, exit 159) even though
   they are no-ops when euid == uid, so the third one is on the path every
   keystroke takes.  Handled by
   `patches/0001-pconsole.c-seteuid-noop-guard.patch`, which guards all three
   sites; test case H5 in test_package/pconsole_pty_test.py pins that down by
   enforcing the boundary with a seccomp-bpf filter.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PconsoleConan(ConanFile):
    name = "pconsole"
    version = "1.2.0"
    description = "Parallel console: type one command into many terminals at once"
    license = "GPL-2.0-or-later"
    homepage = "https://walterdejong.github.io/pconsole/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies: pconsole links libc only (unistd, fcntl,
        # sys/ioctl, termios).  Asserted by the DT_NEEDED check in
        # test_package/pconsole_pty_test.py.
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
        # Upstream's install target writes to the absolute $(bindir) and drops
        # DESTDIR on the floor, so the conan default prefix ("/") would install
        # into the real /bin.  Point --prefix at the package folder instead:
        # `make install` then lands in <package>/bin and pconsole.sh gets the
        # final, relocatable bindir baked into it.
        tc = AutotoolsToolchain(self, prefix=self.package_folder)
        # The autoconf-2.13 `configure` ships no config.guess/config.sub and
        # performs no platform guessing, so neither --host nor --build is needed.
        # Passing --build would be actively harmful: 2.13 parses trailing
        # arguments as host triplets (DRAFT-sntop-1.4.3-autoconf213-*).
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # In-tree build: the 2001-era Makefile.in has no VPATH support, so a
        # tree-out build cannot find config.h or the include/ directory.
        # R33: compiler and flags come from the Autotools toolchain / conan conf.
        with chdir(self, self.source_folder):
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        with chdir(self, self.source_folder):
            autotools.install()
        copy(self, "GPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
