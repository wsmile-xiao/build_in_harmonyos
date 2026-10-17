#!/usr/bin/env python3
"""Conan recipe for roll 2.7.0 — command line dice roller (HarmonyOS PC, aarch64).

roll evaluates dice expressions written in a small, intuitive language and prints
the result: ``1d6``, ``4d6h3`` (keep highest 3), ``4d6l3``, ``4d6HX`` / ``4d6LX``
(drop highest/lowest), ``1d%`` (percentile), ``dF`` (Fudge), ``3d6x10``, filters
(``1d6>3``), comma separated expressions, ``N{...}`` repetition groups, series
sums (``-s``) and the positive-only mode (``-p``).  Upstream is a small autotools
project (``parser.y`` + ``scanner.l`` + ``roll.c``) whose ``make check`` suite is
fully deterministic thanks to the ``--test`` switch (every die is forced to 3).

Adaptation notes (HarmonyOS PC, aarch64; W0: zero third-party dependencies):
    * One portability patch, platform quirk only: the dist tarball's generated
      ``configure`` / ``config.status`` create their helper temp directory with
      ``umask 077 && mktemp -d "./confXXXXXX"`` (fallback ``umask 077 && mkdir``).
      HMDFS forces the setgid bit and remaps the owner UID, so the resulting
      ``drwx--S---`` directory is not writable even by its owner and config.status
      dies with ``./confXXXXXX/subs1.awk: Permission denied`` / "could not setup
      config files machinery" (knowledge base E011/E114 — the standard workaround
      used by the majority of this archive's autotools packages).  The patch drops
      the ``umask 077`` from that block only; upstream sources stay untouched.
      Without it ``configure`` cannot complete on HMDFS; with it
      ``configure`` / ``make`` / ``make check`` are green.
    * build() runs the upstream test suite (``make check``: 3 TAP scripts, 15
      deterministic ``test_expression`` assertions, every one of them
      ``./roll --test ...``) and fails hard unless the log shows exit status 0,
      the automake summary "All 3 tests passed" and all 15 ``Testing '`` lines
      (R9/R51: no skipped or faked tests).  A 600 s ``timeout`` guard turns a
      regression into a clean diagnostic instead of a stuck build.
    * package() uses the upstream ``make install`` (the tarball ships install-sh,
      which works under OHOS/toybox); artifacts: ``bin/roll``,
      ``share/man/man1/roll.1``, the bash-completion file and ``licenses/COPYING``.
      The software-level commands.json declares the CLI tool (R38).

License: GPL-2.0-or-later (upstream roll.spec: ``License: GPLv2+``).
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class RollConan(ConanFile):
    name = "roll"
    version = "2.7.0"
    description = (
        "Command line dice roller with an intuitive expression language "
        "(1d6, 4d6h3, 1d%, dF, filters, repetition groups)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/matteocorti/roll"
    url = "https://github.com/matteocorti/roll"
    topics = ("cli", "dice", "random", "tabletop")

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: accept the whole POSIX family, not `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "roll requires a POSIX host (Linux or OHOS), not {0}".format(
                    self.settings.os
                )
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: three translation units, and it keeps the upstream test log
        # deterministic (the suite is serial by upstream's AUTOMAKE_OPTIONS).
        autotools.make(args=["-j1"])
        self._run_upstream_suite()

    def _run_upstream_suite(self):
        """Run upstream `make check` and hard-fail on any deviation (R9/R51)."""
        log_name = "upstream-tests.log"
        self.run(
            'timeout -k 5 600 make -j1 check > {0} 2>&1; '
            'rc=$?; echo "roll-upstream-check-exit=$rc" >> {0}; cat {0}'.format(log_name),
            ignore_errors=True,
        )
        log_path = os.path.join(self.build_folder, log_name)
        if not os.path.exists(log_path):
            raise ConanException(
                "roll upstream suite: log missing — `make check` did not execute"
            )
        with open(log_path, "r", errors="replace") as handle:
            log_text = handle.read()
        if "roll-upstream-check-exit=124" in log_text or \
                "roll-upstream-check-exit=137" in log_text:
            raise ConanException(
                "roll upstream suite: killed by the 600 s timeout — a regression "
                "made `make check` hang"
            )
        if "roll-upstream-check-exit=0" not in log_text:
            raise ConanException(
                "roll upstream suite: `make check` exited non-zero — see " + log_name
            )
        if "All 3 tests passed" not in log_text:
            raise ConanException(
                "roll upstream suite: automake summary missing — the suite did not "
                "run to completion"
            )
        assertions = len(re.findall(r"Testing '.*' = ", log_text))
        if assertions != 15:
            raise ConanException(
                "roll upstream suite: expected 15 test_expression assertions, "
                "saw {0}".format(assertions)
            )
        self.output.info(
            "roll upstream suite: PASS (make check, 3 scripts / {0} assertions)".format(
                assertions
            )
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
