#!/usr/bin/env python3
"""Conan recipe for splitvt 1.6.6 -- HarmonyOS PC (OHOS) aarch64 adaptation.

Upstream: https://www.libsdl.org/projects/splitvt/ (release archive on the
author's project site).  splitvt splits a vt100-compatible screen in half and
runs a program in each window; it is the classic pseudo-terminal client: two
`/dev/ptmx` allocations, a fork+exec per window and a raw-mode select() loop.

Build system: a hand-written /bin/sh `configure` that compiles `config.c`, runs
it on the build machine and lets it *print* a Makefile.  There is no
configure.ac, no AC_* macro and no CMake, so all "feature detection" is a list
of `exists("/usr/include/<foo>.h", ...)` / `grep("/usr/include", ...)` calls.

OHOS adaptation points (symptoms, evidence and rejected alternatives in
notes.md):

1. The 1993 probes are structurally blind here: `/usr/include` does not exist
   on this platform (headers live in the clang sysroot under
   /data/service/hnp/ohos-sdk.org/...), so config.c answers "no" for unistd.h,
   termio.h, utmp.h and ut_host -- while the compiler *does* predefine `linux`,
   so the generated Makefile still picks the System V `/dev/ptmx` +
   grantpt()/unlockpt()/ptsname() path (the one we want) and writes
   `CC = gcc`.  Probe layer and code layer disagree; the capability macros have
   to be re-supplied by the recipe, and the compiler has to be named.
2. Capability macros go through **CPPFLAGS**, never by overriding CFLAGS: the
   generated Makefile assigns `CFLAGS = -O2 -DSHELL=\"...\" $(PTYOPTS)`, and a
   command-line CFLAGS override both drops upstream's flags and eats one level
   of the quote escaping -- make expands the recipe text and the recipe shell
   parses it again (E575), so SHELL silently stops being a string and the
   compile fails with "use of undeclared identifier 'bin'".  GNU make's built-in
   `.c` rule appends `$(CPPFLAGS)`, which upstream never assigns, so it is the
   collision-free slot.
3. `-include unistd.h` restores the prototypes the probes lost.  That is a
   correctness fix, not hygiene: `ttyname()` is called in utmp.c with no
   visible prototype, so the implicit-int declaration truncates the returned
   pointer on aarch64.  Making the prototypes visible also exposed the BSD
   two-argument `setpgrp(0, 0)` as a hard error (musl only declares POSIX
   `setpgrp(void)`), hence patch 0001.
4. Patches 0002/0003 route the legacy terminal layer onto POSIX termios.  This
   sysroot ships neither `<termio.h>` nor `<sgtty.h>`, so *both* branches of
   misc.c / vttest.c were dead (`struct sgttyb` incomplete, TIOCGETP/TIOCSETP
   and RAW undeclared).  They select the System V branch and alias it onto
   `<termios.h>` (struct termio -> struct termios, TCGETA -> TCGETS,
   TCSETAW -> TCSETS), which keeps the drain-before-set property TCSETAW had and
   leaves glibc builds on the real `<termio.h>` path (guarded by __has_include).
5. Patch 0004 gives `vt_getsel()` a return value: clang 15 makes -Wreturn-type
   an error, so a non-void function falling off the end breaks the build.
6. Patch 0005 is a functional fix, not a compile fix.  `dropctty()` only called
   setsid() for `_POSIX_SOURCE`-style systems and otherwise used
   `setpgrp(0,0)` + TIOCNOTTY; but `TIOCSCTTY`, which pty_open() uses right
   after the fork to attach the slave as the controlling terminal, is only
   permitted to a session leader.  Without setsid() the child never owns its
   pty, so an interactive program started there -- the whole point of splitvt --
   sees itself as a background job and never runs what you type.  The patch
   selects the POSIX route wherever TIOCSCTTY exists.
7. No third-party dependency.  termcap/ncurses is only reachable behind
   `#ifdef TERMCAP`, which config.c enables if `/usr/lib/libtermcap.a` exists;
   it does not, and the non-termcap branch hard-codes the VT100 escape
   sequences, so the linked binary needs `libc.so` only (asserted by the
   OHOS-specific test).  requires() therefore stays empty, and with it R36/W0
   has no dependency left to publish first.
8. Upstream has no test suite (Makefile targets: splitvt, clean, distclean,
   install, install-man) and its install target `mv`s into /usr/local/bin, so it
   is never called and package() installs explicitly.  The one self-report
   upstream exposes to a build is `splitvt -v`; it is executed and asserted in
   build() whenever the binary can run here (can_run).
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# Capability macros the upstream Configure cannot decide on its own, because
# every probe it has is a stat() against a /usr/include that does not exist.
_CAPABILITY_FLAGS = (
    "-DHAVE_UNISTD_H",     # splitvt.c guards <unistd.h> behind this macro
    "-include unistd.h",   # every other TU relied on implicit declarations
)


class SplitvtConan(ConanFile):
    name = "splitvt"
    version = "1.6.6"
    description = ("Split a vt100-compatible terminal into two windows and run "
                   "a separate program in each one")
    license = "GPL-2.0-only"
    homepage = "https://www.libsdl.org/projects/splitvt/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os tests must accept OHOS alongside Linux.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "splitvt needs a UNIX pseudo-terminal (Linux/OHOS), got %s"
                % self.settings.os)

    def generate(self):
        # Brings make(1) and the profile buildenv (PATH, CONFIG_SHELL) into
        # self.run(..., env="conanbuild").
        VirtualBuildEnv(self).generate()

    def _cc(self):
        """C compiler from the Conan conf (R33: never a bare shell $CC)."""
        # conan's own toolchains read this through self.conf (see
        # conan/tools/gnu/autotoolstoolchain.py), not self.conf_info.
        exes = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        cc = exes.get("c")
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables{c} is unset: the generated "
                "upstream Makefile hard-codes CC = gcc, which does not exist "
                "on HarmonyOS PC, so the recipe has to name the compiler")
        return cc

    def _jobs(self):
        return self.conf.get("tools.build:jobs", default=1, check_type=int)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        src = self.source_folder

        # Step 1: let upstream generate its own Makefile.  Run it without
        # arguments so config.c prints what each probe decided; that output is
        # the evidence trail for adaptation point 1.
        self.run('CC="%s" sh ./configure' % cc, cwd=src, env="conanbuild")
        if not os.path.isfile(os.path.join(src, "Makefile")):
            raise ConanException("./configure produced no Makefile")

        # Step 2: compile.  CC has to be given on the make command line because
        # the generated file assigns CC = gcc, and a makefile assignment beats
        # an environment variable.  Capability macros go to CPPFLAGS (see
        # adaptation point 2).
        caps = " ".join(_CAPABILITY_FLAGS)
        self.run('make -j%s CC="%s" CPPFLAGS="%s" splitvt'
                 % (self._jobs(), cc, caps), cwd=src, env="conanbuild")
        exe = os.path.join(src, "splitvt")
        if not os.path.isfile(exe):
            raise ConanException("make did not produce %s" % exe)

        # Step 3: run the one self-check upstream exposes to a build, and fail
        # the build if the banner does not agree with the packaged version.
        if can_run(self):
            self.run('./splitvt -v | grep -F "Splitvt 1.6.6" >/dev/null',
                     cwd=src, env="conanbuild")

    def package(self):
        pkg = self.package_folder
        src = self.source_folder
        # Upstream 'make install' moves (mv) files into /usr/local/bin and has
        # no DESTDIR/PREFIX support, so artifacts are installed explicitly.
        copy(self, "splitvt", src=src, dst=os.path.join(pkg, "bin"),
             keep_path=False)
        os.chmod(os.path.join(pkg, "bin", "splitvt"), 0o755)
        copy(self, "COPYING", src=src, dst=os.path.join(pkg, "licenses"))
        # install-man equivalent: 'cp splitvt.man /usr/local/man/man1/splitvt.1'
        man = os.path.join(pkg, "man", "man1")
        os.makedirs(man, exist_ok=True)
        copy(self, "splitvt.man", src=src, dst=man, keep_path=False)
        os.rename(os.path.join(man, "splitvt.man"),
                  os.path.join(man, "splitvt.1"))
        # Sample configuration and helper scripts.  examples/xsplitvt and
        # examples/menu are /bin/sh wrappers around xterm, which this target
        # does not provide, so they ship as resources and are deliberately not
        # declared in commands.json (see notes.md, known limitations).
        res = os.path.join(pkg, "res", self.name)
        for folder in ("examples", "escapes", "utils"):
            copy(self, "*", src=os.path.join(src, folder),
                 dst=os.path.join(res, folder))
        copy(self, "README", src=src, dst=os.path.join(res, "docs"))
        for doc in ("NOTES", "CHANGES", "TODO", "BLURB", "ANNOUNCE"):
            copy(self, doc, src=src, dst=os.path.join(res, "docs"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
