#!/usr/bin/env python3
"""Conan recipe for sysklogd 1.5.1 -- system log daemon + kernel log daemon.

sysklogd ships two standalone daemons, both produced by one plain Makefile
(there is no configure script, no autotools, no Makefile.am in the tarball):

  * syslogd -- receives log messages on an AF_UNIX datagram socket (the
    /dev/log contract, relocatable with -p) and optionally on UDP/syslog,
    and routes them to files/console per a syslog.conf.
  * klogd   -- pulls kernel log records and forwards them to syslogd.

Both are programs, not libraries, so package_type = "application" and
test_package exercises the installed binaries through their public contract
(the log socket + the CLI) instead of linking a library API.

Packaging decisions that are specific to this upstream:

  * The Makefile hardcodes ``CC= gcc`` (Makefile:20) and a GCC-only flag set
    ``SKFLAGS= ... -O3 -DSYSV -fomit-frame-pointer -fno-strength-reduce``
    (Makefile:23).  Both are overridden from the make command line.
    ``-DSYSV`` is load-bearing and is kept in the replacement flag set:
    syslogd.c picks ``#include <fcntl.h>`` under SYSV (line 530) but
    ``#include <sys/msgbuf.h>`` otherwise (line 533), and sys/msgbuf.h does
    not exist in the OHOS sysroot (verified header sweep, 48 includes).
    ``-fno-strength-reduce`` is a GCC-only option and is dropped.
  * ``make install`` is deliberately not used: its ``install_exec`` rule
    (Makefile:129) hardwires syslogd and klogd into a single recipe line, and
    ``install_man`` needs ``${INSTALL}`` = /usr/bin/install plus
    ``-o root -g root`` ownership.  package() installs by hand instead.
  * ``prefix`` is a private directory inside the Conan build folder (R49/PF6)
    so that nothing can ever land in a shared system prefix; it is passed to
    make even though the install rules are unused, so that a future
    ``make install`` cannot write outside the sandbox.
  * ``LDFLAGS`` is emptied: upstream ``LDFLAGS= -s`` strips at link time, and
    on OHOS the MAC layer rejects binaries rewritten after signing (same
    lesson recorded in archives/a/abduco/0.6 and archives/a/acorn-fdisk/3.0.6).
  * Only the ``syslogd`` and ``klogd`` targets are requested by name.  The
    upstream default target is the same pair, but naming them also guarantees
    the ``test`` target (Makefile:78) is never pulled in -- it builds an
    out-of-tree kernel module (oops.ko, Makefile:141) against
    /lib/modules/$(uname -r)/build, which does not exist on this platform.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# build_type -> optimisation flags (upstream uses -O3; -O2 is the Conan-side
# default and keeps the two daemons' code generation within what clang-15
# was verified against elsewhere in this repository).
_BUILD_TYPE_OPT = {
    "Debug": "-O0 -g",
    "Release": "-O2",
    "RelWithDebInfo": "-O2 -g",
    "MinSizeRel": "-Os",
}


class SysklogdConan(ConanFile):
    name = "sysklogd"
    version = "1.5.1"
    description = (
        "sysklogd: the Linux system log daemon (syslogd) and kernel log "
        "daemon (klogd), packaged for HarmonyOS PC"
    )
    license = "GPL-2.0-only"
    homepage = "https://www.infodrom.org/projects/sysklogd/"
    url = ""  # CI fills this
    topics = ("syslog", "daemon", "logging", "system")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Upstream compiles in place: every rule is "${CC} ${SKFLAGS} ... -c
        # <file>.c", dropping the .o next to the .c, so the build tree is the
        # source tree.
        self.folders.build = "."

    def validate(self):
        # R32: both daemons are Linux-family only (syslog socket, klogctl,
        # /proc filesystem assumptions).
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sysklogd needs a Linux-family kernel, got os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return (compilers or {}).get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)

        cc = self._cc()
        prefix = os.path.join(self.build_folder, "prefix")
        opt = _BUILD_TYPE_OPT.get(str(self.settings.build_type), "-O2")
        # -DSYSV must survive the SKFLAGS override, see the module docstring.
        skflags = f"{opt} -DSYSV -Wall"

        self.run(
            f'make -j1 CC="{cc}" prefix="{prefix}" SKFLAGS="{skflags}" '
            f'LDFLAGS="" syslogd klogd',
            cwd=self.source_folder,
        )

    def package(self):
        sbin = os.path.join(self.package_folder, "sbin")
        man8 = os.path.join(self.package_folder, "share", "man", "man8")
        man5 = os.path.join(self.package_folder, "share", "man", "man5")
        etc = os.path.join(self.package_folder, "etc")
        licenses = os.path.join(self.package_folder, "licenses")

        src = self.source_folder

        # Hand-installed because upstream install_exec/install_man cannot be
        # used (see the module docstring).  -m 500 is what install_exec used.
        for prog in ("syslogd", "klogd"):
            built = os.path.join(src, prog)
            if not os.path.isfile(built):
                raise ConanException(
                    f"build produced no {prog}; expected it in {src}"
                )
            copy(self, prog, src, sbin, keep_path=False)
            try:
                os.chmod(os.path.join(sbin, prog), 0o755)
            except OSError:  # hmdfs ignores chmod; keep the install going
                pass

        for page in ("sysklogd.8", "syslogd.8", "klogd.8"):
            copy(self, page, src, man8, keep_path=False)
        copy(self, "syslog.conf.5", src, man5, keep_path=False)

        # Upstream's annotated sample configuration.  Not activated by the
        # recipe: -f must be passed by the operator, which keeps this package
        # from silently claiming the system log socket.
        copy(self, "syslog.conf", src, etc, keep_path=False)
        copy(self, "COPYING", src, licenses, keep_path=False)

    def package_info(self):
        # An application package: nothing to link, nothing to include.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["sbin"]
