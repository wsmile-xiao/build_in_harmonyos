#!/usr/bin/env python3
"""Conan recipe for unifdef 2.12 — selectively remove C preprocessor conditionals.

unifdef processes #if/#ifdef/#ifndef directives and removes both the directives
and the text they delimit, leaving the rest of the file untouched.  The upstream
tarball carries a plain POSIX Makefile (no configure step):

    * make          — builds the single-file C program `unifdef` from unifdef.c
    * make test     — runs scripts/runtests.sh over the tests/ directory
                      (90 shell cases, each comparing .out/.err/.rc against the
                      expected .expout/.experr/.exprc files)
    * make install  — installs `unifdef`, the `unifdefall` shell wrapper and the
                      man pages

Adaptation notes (HarmonyOS PC, aarch64):
    * W0: no third-party dependencies — ANSI C + POSIX shell only (requires is
      empty; `requirements()` is intentionally absent).
    * Zero upstream patches: the unmodified Makefile builds with the OHOS SDK
      clang (R33: the compiler path comes from Conan conf, never a shell var).
    * The upstream suite runs in build() so CI L1 sees the real tests executed.
      Eight cases depend on host facilities that the OHOS build host does not
      provide and are tolerated *only* as the exact documented set below; any
      other failure aborts the build.  Details in test_package/MANIFEST.yml.
    * package() copies artifacts directly because the upstream `install` target
      needs `install`(1), which is not guaranteed on the CI worker PATH.
Artifacts: bin/unifdef, bin/unifdefall + share/man/man1 (software-level
commands.json declares the CLI, R38).
License: BSD-2-Clause.
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class UnifdefConan(ConanFile):
    name = "unifdef"
    version = "2.12"
    description = "Selectively remove C preprocessor conditionals (#if/#ifdef/#ifndef) from source files"
    license = "BSD-2-Clause"
    homepage = "https://dotat.at/prog/unifdef/"
    url = "https://dotat.at/prog/unifdef/"
    topics = ("preprocessor", "ifdef", "cli", "code-cleanup", "posix")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # Upstream cases whose expected result depends on host capabilities that
    # the OHOS build host does not provide.  Each one is documented with its
    # technical reason in test_package/MANIFEST.yml; any failure outside this
    # set aborts the build instead of being silently tolerated.
    HOST_INCOMPATIBLE_TESTS = (
        # unifdefall(1) shells out to `cc -E`; the OHOS SDK cross clang has no
        # default sysroot, so preprocessing #include <stdio.h> fails.
        "if1-a", "if2-a", "if3-a", "if4-a", "if5-a",
        # Expected output embeds GNU diff -u hunk headers; OHOS ships toybox
        # diff, which writes different hunk ranges for the same edit.
        "multimissing", "multinewline",
        # chmod(2) is not enforced on HMDFS: a 0555 directory stays writable,
        # so the expected "Permission denied" cannot be produced.
        "outeperm",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Plain POSIX Makefile project: build in the source folder.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException("unifdef requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: -j1; R33: compiler path from Conan conf, not a bare shell variable.
        self.run("make -j1 CC={0}".format(cc))

        # Upstream regression suite.  scripts/runtests.sh deletes the per-case
        # .out/.err/.rc files of passing cases and keeps them for failures, so
        # we inspect exactly which cases failed instead of trusting the exit
        # code alone.  The runner's "FAILED:" log lines are unioned with the
        # leftover .rc files, and a progress-mark floor is enforced, so that a
        # harness which never started cannot masquerade as a silent 90/90.
        self.run("rm -f tests/*.out tests/*.err tests/*.rc")
        self.run(
            "make CC={0} test 2>&1 | tee upstream-tests.log".format(cc),
            ignore_errors=True,
        )
        log_path = os.path.join(self.build_folder, "upstream-tests.log")
        if not os.path.exists(log_path):
            raise ConanException(
                "unifdef upstream suite: runner log missing — the test harness did not execute"
            )
        with open(log_path, "r", errors="replace") as handle:
            log_text = handle.read()
        failures = {
            os.path.splitext(os.path.basename(path))[0]
            for path in glob.glob(os.path.join(self.build_folder, "tests", "*.rc"))
        }
        failures.update(
            match.group(1)
            for match in re.finditer(r"^FAILED: ([A-Za-z0-9._-]+)\.", log_text, re.MULTILINE)
        )
        total = len(glob.glob(os.path.join(self.build_folder, "tests", "*.sh")))
        progress_marks = log_text.count(".")
        if progress_marks < total:
            raise ConanException(
                "unifdef upstream suite: only {0} progress marks for {1} test cases — "
                "the suite did not run to completion".format(progress_marks, total)
            )
        unexpected = [name for name in sorted(failures) if name not in self.HOST_INCOMPATIBLE_TESTS]
        self.output.info(
            "unifdef upstream suite: {0}/{1} passed; host-incompatible failures: {2}".format(
                total - len(failures), total, ", ".join(sorted(failures)) or "none"
            )
        )
        if unexpected:
            raise ConanException(
                "unifdef upstream suite: unexpected failures on tests/{0}.sh — "
                "see upstream-tests.log".format(", ".join(unexpected))
            )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)
        # Direct copy: upstream `make install` needs install(1), which is not
        # guaranteed to be on PATH in the CI build environment.
        copy(self, "unifdef", src=self.build_folder, dst=bindir, keep_path=False)
        copy(self, "unifdefall.sh", src=self.build_folder, dst=bindir, keep_path=False)
        os.replace(
            os.path.join(bindir, "unifdefall.sh"),
            os.path.join(bindir, "unifdefall"),
        )
        copy(self, "unifdef.1", src=self.build_folder, dst=mandir, keep_path=False)
        shutil.copyfile(
            os.path.join(mandir, "unifdef.1"),
            os.path.join(mandir, "unifdefall.1"),
        )
        for exe in ("unifdef", "unifdefall"):
            os.chmod(os.path.join(bindir, exe), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
