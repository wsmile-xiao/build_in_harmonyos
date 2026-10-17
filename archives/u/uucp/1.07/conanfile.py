#!/usr/bin/env python3
"""Conan recipe for GNU Taylor UUCP 1.07 — Unix-to-Unix copy protocol suite.

Taylor UUCP is the GNU implementation of UUCP: file transfer (uucp/uux),
spool execution (uuxqt), the transfer daemon (uucico), chat/dialing helpers
and the `cu` serial-connection program.  The upstream release tarball carries
a pre-generated autoconf-2.13 `configure` and automake-1.4 `Makefile.in`s:

    * ./configure && make   — builds 11 programs (4 sbin + 7 bin) plus the
                              manual test driver `tstuu` (noinst) and the
                              `uusched`/`uuto` shell scripts
    * make check            — automake's empty check target (no TESTS var):
                              the upstream suite has zero automated cases;
                              the only upstream test artifact is tstuu.c
    * make install          — NOT used: install-exec-hook runs `chown $(OWNER)`
                              (OWNER = uucp) and `chown root`, which a non-root
                              build user cannot do (EPERM); package() copies
                              directly.

Adaptation notes (HarmonyOS PC, aarch64):
    * W0: no third-party dependencies at all.  configure.in has zero
      PKG_CHECK_MODULES / AM_PATH_* / AC_MSG_ERROR.  All five AC_CHECK_LIB
      probes (sun, nsl_s, nsl, socket, xti) are optional and non-fatal — an
      AC_CHECK_LIB failure simply leaves the library out of LIBS.  Four of them
      (nsl_s, nsl, socket, xti) sit inside a `case $LIBS in ... ;; *)` guard
      that short-circuits the probe when a sibling is already present; `sun`
      (configure.in:64) is a plain top-level probe.  The link line is
      `LDADD = unix/libunix.a uuconf/libuuconf.a lib/libuucp.a`, all three
      being noinst_LIBRARIES built from the same tree.
    * autoconf-2.13 cross behaviour (verified by reading the generated
      configure): "checking whether the C compiler works" only requires a
      successful *link*; running ./conftest is attempted separately and its
      failure merely sets ac_cv_prog_cc_cross=yes.  Every AC_TRY_RUN in
      configure.in carries an explicit cross-compiling fallback —
      uucp_cv_sys_ftime_ok=runtime (documented by upstream as "if we're
      cross-configuring we accept that ftime exists") and the statfs family
      defaults to no (musl's compile-only statvfs probe hits first, so the
      whole chain is short-circuited).  No configure patch needed.
    * sysexits.h (used by uux.c / unix/xqtsub.c) exists in the OHOS SDK
      sysroot; uux.c additionally has #ifndef fallback defines.
    * all-am depends on $(INFO_DEPS): `touch uucp.info` before make prevents
      a rebuild attempt (the build host has no makeinfo; the pre-generated
      uucp.info ships in the tarball and carries no version.texi dependency).
    * ftime/poll/select/times all exist in musl; missing SysV-era functions
      are covered by the package's own lib/ LIBOBJS replacements.
Artifacts: bin/{uucico,uuxqt,uuchk,uuconv,uux,uucp,uustat,uuname,uulog,
uupick,cu,uusched,uuto} + share/man + share/info/uucp.info (software-level
commands.json declares the CLI set, R38).
License: GPL-2.0-or-later.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import load_toolchain_args
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UucpConan(ConanFile):
    name = "uucp"
    version = "1.07"
    description = (
        "GNU Taylor UUCP: Unix-to-Unix copy protocol suite "
        "(uucico, uuxqt, uucp, uux, cu and companions)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/uucp/"
    url = "https://www.gnu.org/software/uucp/"
    topics = ("uucp", "file-transfer", "serial", "modem", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "conandata.yml"

    SBIN_PROGRAMS = ("uucico", "uuxqt", "uuchk", "uuconv")
    BIN_PROGRAMS = ("uux", "uucp", "uustat", "uuname", "uulog", "uupick", "cu")
    BIN_SCRIPTS = ("uusched", "uuto")
    MAN1_PAGES = ("uux.1", "uucp.1", "uustat.1", "cu.1")
    MAN8_PAGES = ("uucico.8", "uuxqt.8")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # autoconf-2.13/automake-1.4 era project: build in the source folder
        # (VPATH support of that generation is not worth the risk here).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Flat install prefix: package() copies files explicitly, so the
        # configure-time directories only steer uusched/uuto script rewriting
        # (@SBINDIR@/@BINDIR@ substitutions) and NEWCONFIGLIB default text.
        tc.configure_args.extend(
            [
                "--prefix=/",
                "--sbindir=/bin",
                "--bindir=/bin",
                "--mandir=/share/man",
                "--infodir=/share/info",
            ]
        )
        tc.generate()

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException("uucp requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args"
        )
        config_shell = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        build_folder = os.path.abspath(self.build_folder)
        os.environ["PWD"] = build_folder
        self.run(
            'PWD="{0}" CONFIG_SHELL="{1}" "{1}" "{2}" {3} 2>&1 | tee configure.log'.format(
                build_folder, config_shell, configure, configure_args
            )
        )

        # Timestamp hygiene: keep generated artifacts newer than their inputs
        # so automake-1.4 rules never try to re-run auto* tools (the host has
        # no autoconf/automake/makeinfo).
        src = self.source_folder
        for generated, inputs in (
            ("configure", ("configure.in", "aclocal.m4")),
            ("Makefile.in", ("Makefile.am",)),
            ("lib/Makefile.in", ("lib/Makefile.am",)),
            ("unix/Makefile.in", ("unix/Makefile.am",)),
            ("uuconf/Makefile.in", ("uuconf/Makefile.am",)),
            ("uucp.info", ("uucp.texi",)),
        ):
            gpath = os.path.join(src, generated)
            if not os.path.exists(gpath):
                raise ConanException(
                    "uucp: expected upstream-generated artifact missing: {0}".format(
                        generated
                    )
                )
            for dep in inputs:
                dpath = os.path.join(src, dep)
                if os.path.exists(dpath) and os.path.getmtime(dpath) >= os.path.getmtime(gpath):
                    os.utime(gpath, None)
                    break

        autotools = Autotools(self)
        autotools.make(args=["-j1"])

        # Upstream test entry point, executed for the record: automake-1.4
        # emits `check: check-recursive` -> `check-am: all-am` with no TESTS
        # variable, so the whole suite is an empty pass.  The run is kept in
        # upstream-check.log as the evidence that the entry was really driven
        # and produced zero automated cases.
        self.run("make check 2>&1 | tee upstream-check.log", ignore_errors=True)

        for program in self.SBIN_PROGRAMS + self.BIN_PROGRAMS + ("tstuu",):
            if not os.path.exists(os.path.join(build_folder, program)):
                raise ConanException(
                    "uucp build did not produce expected program: {0}".format(program)
                )
        for script in self.BIN_SCRIPTS:
            if not os.path.exists(os.path.join(build_folder, script)):
                raise ConanException(
                    "uucp build did not produce expected script: {0}".format(script)
                )
        with open(os.path.join(build_folder, "upstream-check.log"), errors="replace") as fh:
            check_log = fh.read()
        self.output.info(
            "uucp upstream check: automake reports '{0}' (no TESTS variable in any "
            "Makefile.in — 0 automated upstream cases)".format(
                "nothing to be done" if "Nothing to be done" in check_log else "see log"
            )
        )

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        man1dir = os.path.join(self.package_folder, "share", "man", "man1")
        man8dir = os.path.join(self.package_folder, "share", "man", "man8")
        infodir = os.path.join(self.package_folder, "share", "info")
        licdir = os.path.join(self.package_folder, "licenses")
        for directory in (bindir, man1dir, man8dir, infodir, licdir):
            os.makedirs(directory, exist_ok=True)
        # Direct copy instead of `make install`: the upstream install-exec-hook
        # (Makefile.am:79-94) runs `chown $(OWNER)` with OWNER = uucp, plus a
        # `chown root` in its HAVE_MKDIR=0 fallback branch.  A non-root build
        # user cannot chown to another owner (EPERM).  (Note: the `chmod 4555`
        # and `chmod 100` calls are not by themselves blocking — the owner can
        # set setuid on its own file, and the `chmod 100` uudir branch is not
        # even taken here because config.h defines HAVE_MKDIR 1.)
        for program in self.SBIN_PROGRAMS + self.BIN_PROGRAMS:
            copy(self, program, src=src, dst=bindir, keep_path=False)
        for script in self.BIN_SCRIPTS:
            copy(self, script, src=src, dst=bindir, keep_path=False)
        for page in self.MAN1_PAGES:
            copy(self, page, src=src, dst=man1dir, keep_path=False)
        for page in self.MAN8_PAGES:
            copy(self, page, src=src, dst=man8dir, keep_path=False)
        copy(self, "uucp.info", src=src, dst=infodir, keep_path=False)
        copy(self, "COPYING", src=src, dst=licdir, keep_path=False)
        for name in self.SBIN_PROGRAMS + self.BIN_PROGRAMS + self.BIN_SCRIPTS:
            os.chmod(os.path.join(bindir, name), 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
