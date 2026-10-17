#!/usr/bin/env python3
"""Conan recipe — yasr 0.6.9 (autotools, console screen reader).

yasr ("Yet Another Screen Reader") runs a shell inside a pty, intercepts the
I/O stream and speaks the screen through a TTS device.  Upstream lives on
SourceForge (https://yasr.sourceforge.net, SourceForge project "yasr"); the
2008-era release archive is byte-identical to the Debian .orig tarball, so the
official SourceForge URL is used (R39/PF7).  Build system: autoconf 2.61 /
automake 1.10 (a *pre-generated* configure ships in the tarball, so the recipe
never bootstraps autotools).

Deps: none (W0).  configure.in only probes libc/libutil/gettext and the OHOS
musl sysroot satisfies all of it first-hand: config.h ends up with
HAVE_OPENPTY / HAVE_FORKPTY / HAVE_LOGIN_TTY / HAVE_CFMAKERAW / HAVE_PTY_H /
HAVE_LIBUTIL = 1, while the generated yasr/Makefile has "LIBOBJS =" and
"INTLLIBS =" empty — i.e. no bundled replacement object is compiled and no
libintl is linked.  Hence no requires()/tool_requires() at all.

Artifacts: bin/yasr only (software-level commands.json declares the CLI, R38).
yasr/keytest/Makefile.am builds keytest as noinst_PROGRAMS (an interactive
keyboard diagnostic, not installed) and the top-level Makefile.am builds
acclogin only under the YASR_SUN (Solaris) conditional, so neither is packaged.

Adaptation (HarmonyOS PC aarch64) — four patches, no --build/--host override
(forbidden by E007/E072/E122):
  * 0001 config.guess: teach the 2007-07-22 script to recognise
    "uname -s = HarmonyOS".  That vintage has no GUESS= accumulation
    mechanism, so the branch must print the triplet and exit itself.
  * 0002 config.sub: accept the linux-ohos kernel/OS pair in the 2007-06-28
    script (KERNEL-OS split list + OS whitelist, the latter placed before the
    generic -linux*) branch which would otherwise rewrite the triplet to
    -linux-gnu-ohos).
  * 0003 configure: umask 077 -> 022 for config.status' tmp dir (E011).  The
    build user is not the owner of the tree on this host, so a 0700 directory
    is not writable by it; config.status then silently writes no
    Makefile/config.h while configure still exits 0.
  * 0004 yasr/yasr.h: guard the private openpty()/forkpty() prototypes with
    HAVE_OPENPTY/HAVE_FORKPTY — they clash with <pty.h>'s const-qualified
    declarations and are dead weight once the bundled replacements are not
    built.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class YasrConan(ConanFile):
    name = "yasr"
    version = "0.6.9"
    description = (
        "yasr - Yet Another Screen Reader: a lightweight console screen "
        "reader that runs a shell in a pty and speaks the screen through a "
        "TTS device"
    )
    license = "LGPL-2.0-or-later"
    homepage = "https://yasr.sourceforge.net"
    url = "https://sourceforge.net/projects/yasr/"
    topics = ("screen-reader", "accessibility", "tts", "pty", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan dependencies (W0): the only externals configure probes are
        # libutil (openpty/forkpty/login_tty) and gettext, both satisfied by
        # the OHOS musl sysroot — see the docstring for the measured evidence.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R1 argument minimalism: --prefix is all this configure needs.  The
        # OHOS triplet is made acceptable by patches 0001/0002 rather than by
        # --build/--host/--target (E007/E072/E122 forbid that shortcut,
        # because it makes configure skip every AC_RUN_IFELSE probe).
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: GNU make 4.4.1 cannot create its jobserver FIFO on this host
        # ("jobserver mkfifo: .../GMfifoNNNN: Operation not permitted"), so no
        # parallel top-level make is attempted.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Application package: put the installed binary on PATH for consumers
        # (test_package/L2 resolve bin/yasr without relying on the caller's
        # environment).
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
