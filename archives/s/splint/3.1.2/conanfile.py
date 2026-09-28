#!/usr/bin/env python3
"""Conan recipe for splint 3.1.2 — annotation-assisted static analyser for C.

Upstream : https://splint.org/downloads/splint-3.1.2.src.tgz  (GPL-2.0-or-later)
Build    : GNU autotools (hand-written configure + GNU make)
Platform : HarmonyOS PC — OHOS / aarch64 / device-native build

OHOS adaptation notes (every item below is backed by a patch in patches/ and was
verified on device; see notes.md for the raw command output):

* ``config.guess`` (2008 vintage) cannot identify HarmonyOS ("unable to guess system
  type"), so ``--build`` is pinned to a triplet the bundled ``config.sub`` accepts.
* HMDFS rejects ``umask 077 && mkdir`` (setgid directory + UID remapping, knowledge
  item E011), so ``0001-configure.patch`` lowers configure's private tmpdir umask to
  022 — otherwise ``config.status`` aborts with "cannot create a temporary directory
  in .".
* GNU make's jobserver FIFO cannot be created over HMDFS, hence the whole build and
  the upstream test suite run serially (``-j1``).
* The OHOS libc does not provide ``__pid_t``; ``0005-src-osd.c.patch`` spells the local
  variable as ``int`` (the function already returns ``int``).
* flex's ``libfl`` is not required: ``0004-src-globals.c.patch`` defines ``yywrap()``
  unconditionally instead of only under ``#ifdef WIN32``, so linking succeeds with an
  empty ``@LEXLIB@``.
* ``/tmp`` is a read-only ``erofs`` mount on OHOS (knowledge item E002), so
  ``0003-src-context.c.patch`` lets the POSIX ``TMPDIR`` environment variable override
  the compiled-in default temp directory; the recipe also points ``TMPDIR`` at a
  writable directory while running the upstream test suite.
* bison >= 3 emits ``signature.tab.h``; ``0002-src-Makefile.in.patch`` carries the
  upstream fix that pipes the generated parser through ``sed`` to rewrite that include
  to ``signature_gen.h``.

Upstream test suite: the upstream ``test/`` directory (``make check`` == ``fulltest``,
133 checks).  It is executed from ``build()``; see ``_run_upstream_tests()`` for the
tolerated environment-dependent failures and ``test_package/MANIFEST.yml`` for the
declaration matching the numbers reported in the pull request.
"""

import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SplintConan(ConanFile):
    name = "splint"
    version = "3.1.2"
    description = "splint — annotation-assisted static analysis tool for C"
    license = "GPL-2.0-or-later"
    homepage = "https://splint.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Command line tool: ships bin/splint plus its .lcd model library.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Number of checks the upstream suite runs (test/Makefile, `fulltest` target).
    _upstream_checks = 133

    # Two upstream checks cannot pass on this platform because upstream's own fixtures
    # assume a host filesystem layout OHOS does not provide.  A failing check is only
    # tolerated when its recorded output carries the documented symptom below, so a
    # failure for any other reason (or with a different root cause) still breaks the
    # build.  The suite is never edited or skipped to obtain a green run.
    _tolerated_failures = {
        "rc": "Temporary file for pre-processor output already exists.",
        "utypes": "Cannot find include file sys/types.h on search path:",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Upstream expects a srcdir build: configure/Makefile.in sit in the source root
        # and test/ refers to ../src/splint relatively (abduco precedent).
        self.folders.build = "."
        # Consumed by AutotoolsToolchain (--bindir/--datarootdir) and published to
        # consumers: the executable in bin/, the .lcd model library in share/splint/lib.
        self.cpp.package.bindirs = ["bin"]
        self.cpp.package.resdirs = ["share"]

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # splint's configure is autoconf 2.57 (2003 era): it rejects the toolchain's
        # default install flags (--datarootdir/--oldincludedir and the ${prefix}-relative
        # forms).  Replace them with the only ones this configure understands; the DESTDIR
        # used by `make install` still redirects everything into the package folder.
        tc.configure_args = [
            "--prefix=/",
            # config.guess cannot identify HarmonyOS ("unable to guess system type");
            # this triplet is accepted by the bundled config.sub and is the one used by
            # the verified device build.
            "--build=aarch64-unknown-linux-gnu",
        ]
        tc.generate()

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "splint/3.1.2 is adapted for Linux and OHOS only, got os={}".format(
                    self.settings.os
                )
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "splint/3.1.2 supports OHOS armv8 only, got arch={}".format(self.settings.arch)
            )

        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Serial build: HMDFS cannot host GNU make's jobserver FIFO.
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run upstream `make check` (test/Makefile `fulltest`) and validate the result."""
        tmpdir = os.path.join(self.build_folder, "splint-tmpdir")
        os.makedirs(tmpdir, exist_ok=True)
        log = os.path.join(self.build_folder, "upstream-tests.log")

        # TMPDIR: /tmp is read-only on OHOS (E002).  0003-src-context.c.patch makes
        # splint honour TMPDIR for its pre-processor scratch files, so hand the suite a
        # writable directory instead of patching upstream's test fixtures.
        #
        # Run make from inside test/ (upstream does the same in src/Makefile.in:
        # "cd ../test; ${MAKE}").  `make -C test` makes every recipe shell start with a
        # getcwd() failure on HMDFS ("shell-init: error retrieving current directory:
        # getcwd: cannot access parent directories: Not supported"), and since the suite
        # captures each check's stderr that noise fails all 133 comparisons.
        command = "TMPDIR={} make check -j1 > {} 2>&1".format(
            shlex.quote(tmpdir), shlex.quote(log)
        )
        self.run(command, cwd=os.path.join(self.build_folder, "test"))

        report = load(self, log)
        checked, failed, current = [], [], None
        for line in report.splitlines():
            match = re.match(r"Checking (\S+)\.\.\.", line)
            if match:
                current = match.group(1)
                checked.append(current)
            elif "*** FAIL ***" in line and current:
                failed.append(current)

        if len(checked) < self._upstream_checks:
            raise ConanException(
                "upstream test suite aborted early: {} of {} checks ran, see {}".format(
                    len(checked), self._upstream_checks, log
                )
            )

        unexpected = []
        for name in failed:
            out_file = os.path.join(self.build_folder, "test", name + ".out")
            symptom = self._tolerated_failures.get(name)
            if symptom is None or not os.path.exists(out_file) or symptom not in load(
                self, out_file
            ):
                unexpected.append(name)
        if unexpected:
            raise ConanException(
                "upstream test suite reported unexpected failures ({} of {} checks), "
                "see {}: {}".format(len(failed), len(checked), log, ", ".join(unexpected))
            )

        self.output.info(
            "upstream test suite: {}/{} checks passed ({} environment-dependent "
            "failures: {})".format(
                len(checked) - len(failed),
                len(checked),
                len(failed),
                ", ".join(failed) or "none",
            )
        )

    def package(self):
        Autotools(self).install(args=["-j1"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        # splint looks its .lcd model files up on LARCH_PATH; publish the packaged
        # library directory so consumers get a working tool through VirtualRunEnv.
        self.runenv_info.define_path(
            "LARCH_PATH", os.path.join(self.package_folder, "share", "splint", "lib")
        )
