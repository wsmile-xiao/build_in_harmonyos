#!/usr/bin/env python3
"""Conan recipe for pcc (Portable C Compiler) on HarmonyOS PC.

What this package is
--------------------
pcc is built as a *native tool* for HarmonyOS PC: the result is a C compiler
that runs on aarch64 HarmonyOS devices.

Target selection (see notes.md for the full reasoning)
------------------------------------------------------
Upstream pcc has no aarch64 code generator (arch/ holds amd64, arm(32-bit),
hppa, i386, i86, m16c, m68k, mips, mips64, nova, pdp10, pdp11, pdp7, powerpc,
sparc64 and vax), and configure.ac aborts on an unmapped target CPU with
"'$target' is not (yet) supported by pcc".  Building an aarch64 *target* back
end is out of scope for an adaptation task, so this recipe builds pcc as a
HarmonyOS-native compiler whose default target triple is ``amd64-linux`` --
the same shape as the already-accepted chibicc package in this archive.

``--target`` is part of what this product *is* (a retargetable compiler has to
be told which back end to emit), not a platform-detection workaround.  The
*host* triple is never passed: patches/0001 teaches the bundled
config.guess/config.sub about HarmonyOS, so upstream's own AC_CANONICAL_TARGET
resolves the host natively -- the same job `scripts/patch-autotools-ohos.pl`
does for newer autotools trees, adapted to this project's 2014 vintage copies.

Local verifiability
-------------------
OHOS dynamically linked binaries cannot execute off-device (error E544), so
the compiler is linked statically.  That keeps the package runnable wherever
the OHOS binaries and the build host differ, and removes any runtime coupling
to /lib/ld-musl-aarch64.so.1.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PccConan(ConanFile):
    name = "pcc"
    version = "1.2.0-devel-20220331"
    description = "Portable C Compiler (pcc) - a small, self-contained C compiler for HarmonyOS PC"
    license = "BSD-2-Clause"
    homepage = "https://github.com/IanHarvey/pcc"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _target_triplet = "amd64-linux"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS must be treated as a Linux-like platform, not skipped.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux/OHOS hosts, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # See the module docstring: the target is spelled out because pcc is a
        # retargetable compiler, the host is deliberately left to config.guess.
        tc.configure_args.append(f"--target={self._target_triplet}")
        # pcc is 1990s-era C: several translation units rely on tentative
        # definitions, which GCC >= 10 / clang >= 11 no longer merge by default
        # (ld.lld: error: duplicate symbol: lineno).
        tc.extra_cflags.append("-fcommon")
        # Static link so the package is runnable off-device (see module docstring).
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        self._run_upstream_tests()

    def _make_program(self):
        return self.conf.get("tools.gnu:make_program", default="make") or "make"

    def _run_upstream_tests(self):
        """Run upstream's preprocessor regression suite and enforce its verdict.

        Upstream ships no `check` target; the only test suite is cc/cpp/tests,
        driven by the `test` rule of cc/cpp/Makefile.in (test1..test18 against
        res1..res18, plus the res15C/res16C `-C` variants).  That rule writes
        its results next to the inputs (`> tests/run<N>`), which assumes an
        in-tree build, so the corpus is replicated into the build tree and the
        upstream rule then runs unmodified.

        The rule chains every comparison with `;`, so it prints mismatches but
        still exits 0.  The comparisons are therefore repeated here, which is
        what makes a regression fail the build instead of scrolling past.
        """
        tests_src = os.path.join(self.source_folder, "cc", "cpp", "tests")
        tests_build = os.path.join(self.build_folder, "cc", "cpp", "tests")
        if not os.path.isdir(tests_build):
            shutil.copytree(tests_src, tests_build)

        self.run(
            f'"{self._make_program()}" -C cc/cpp test',
            cwd=self.build_folder,
            env="conanbuild",
        )

        checked, failed = 0, []
        for n in range(1, 19):
            for tag, expected_name, produced_name in (
                ("", f"res{n}", f"run{n}"),
                ("-C", f"res{n}C", f"run{n}C"),
            ):
                expected = os.path.join(tests_build, expected_name)
                if not os.path.isfile(expected):
                    continue
                produced = os.path.join(tests_build, produced_name)
                checked += 1
                if not os.path.isfile(produced):
                    failed.append(f"test{n}{tag}: no output")
                elif open(produced, "rb").read() != open(expected, "rb").read():
                    failed.append(f"test{n}{tag}: output differs from {expected_name}")
        if failed:
            raise ConanException(
                "upstream preprocessor tests failed: " + "; ".join(failed)
            )
        self.output.info(
            f"upstream preprocessor tests: {checked} comparisons, 0 failures"
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # The driver locates its own back end by name (cc/cpp/ccom), not by an
        # absolute path, so both directories have to be visible on PATH.
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "libexec")
        )
