#!/usr/bin/env python3
"""Conan recipe for xa 2.4.1 (xa65) — 6502/R65C02/65816 cross-assembler.

xa is a two-pass cross-assembler for the 6502/65C02/65816 CPU families shipped
with its companion o65 toolchain:

    * xa       — the assembler itself (raw executables or o65 objects)
    * file65   — o65 object/executable information dumper
    * ldo65    — o65 linker
    * reloc65  — o65 relocator
    * uncpk    — C64 cpk archive manager
    * printcbm — Commodore BASIC listing dumper (deprecated upstream)

Adaptation notes (HarmonyOS PC, aarch64):
    * W0: no third-party dependencies — ANSI C + libc only (`requirements()`
      intentionally absent).
    * The upstream plain Makefile builds all six binaries with the OHOS SDK
      clang (R33: the compiler path comes from the Conan conf, never a bare
      shell variable).
    * The GitHub tag archive stores the project in a `xa/` subdirectory next
      to a repository-level README; source() flattens that layout so build(),
      patch application and packaging all happen at the project root.
    * The upstream regression suite (tests/harness + tests/hextool, Perl) is
      patched for OHOS shebang portability (see patches/ and
      reports/test-report.md); no assertion was changed and all 44 cases pass
      on the device.  build() runs the suite and fails hard if it does not
      complete successfully.
    * package() copies artifacts directly: upstream `make install` needs
      install(1), which OHOS/toybox does not provide.

Artifacts: bin/{xa,file65,ldo65,reloc65,uncpk,printcbm} + share/man/man1
(software-level commands.json declares the CLI tools, R38).
License: GPL-2.0-or-later.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class XaConan(ConanFile):
    name = "xa"
    version = "2.4.1"
    description = "6502/65C02/65816 cross-assembler with the o65 linker/relocator utilities"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/fachat/xa65"
    url = "https://github.com/fachat/xa65"
    topics = ("assembler", "6502", "65816", "o65", "retro-computing", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    BINARIES = ("xa", "file65", "ldo65", "reloc65", "uncpk", "printcbm")
    MANPAGES = ("xa.1", "file65.1", "ldo65.1", "reloc65.1", "uncpk.1", "printcbm.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Plain upstream Makefile project: build in the source folder.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The xa65 GitHub archive keeps the project in xa/ with a small
        # repository-level README next to it.  Flatten it so every later step
        # (patches, make, instrumentation) works on the project root.
        nested = os.path.join(self.source_folder, "xa")
        if os.path.isdir(nested):
            for entry in os.listdir(nested):
                shutil.move(os.path.join(nested, entry), os.path.join(self.source_folder, entry))
            os.rmdir(nested)
        repo_readme = os.path.join(self.source_folder, "README")
        if os.path.isfile(repo_readme):
            os.remove(repo_readme)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException("xa requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: -j1; R33: compiler path from Conan conf, not a bare shell variable.
        self.run('make -j1 CC="{0}" LD="{0}"'.format(cc))

        # Upstream regression suite (44 Perl-driven cases; the harness compares
        # assembler/linker/relocator output byte-for-byte).  The harness must
        # run with cwd=tests/ like upstream's `make test` target, otherwise it
        # would scan the project root (src/, man/, ...) instead of the test
        # directories.  A missing `perl` must abort the build: the suite is the
        # only upstream verification and skipping it silently would be worse
        # than a hard failure.
        self.run(
            'if ! command -v perl >/dev/null 2>&1; then '
            '  echo "xa upstream suite: perl not found on PATH"; exit 1; '
            'fi; '
            '( cd tests && perl harness -tests=ALL -cc="{0}" -cflags="-O2 -g" -make=make ) '
            '> upstream-tests.log 2>&1; '
            'rc=$?; echo "xa-upstream-suite-exit=$rc" >> upstream-tests.log; '
            'cat upstream-tests.log'.format(cc),
            ignore_errors=True,
        )
        log_path = os.path.join(self.build_folder, "upstream-tests.log")
        if not os.path.exists(log_path):
            raise ConanException(
                "xa upstream suite: log missing — the test harness did not execute"
            )
        with open(log_path, "r", errors="replace") as handle:
            log_text = handle.read()
        if "xa-upstream-suite-exit=0" not in log_text:
            raise ConanException(
                "xa upstream suite: the harness exited non-zero — see upstream-tests.log"
            )
        marker = re.search(r"## ALL SELECTED TESTS PASS \((.+), n=(\d+)\) ##", log_text)
        if not marker:
            raise ConanException(
                "xa upstream suite: no 'ALL SELECTED TESTS PASS' marker — "
                "the suite did not run to completion"
            )
        count = int(marker.group(2))
        if count <= 0:
            raise ConanException("xa upstream suite: harness reported n=0 tests")
        self.output.info(
            "xa upstream suite: {0}/{0} passed ({1})".format(count, marker.group(1))
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)
        # Direct copy: upstream `make install` needs install(1), which is not
        # guaranteed to be on PATH in the build environment.
        for binary in self.BINARIES:
            copy(self, binary, src=self.build_folder, dst=bindir, keep_path=False)
            os.chmod(os.path.join(bindir, binary), 0o755)
        for manpage in self.MANPAGES:
            copy(
                self,
                manpage,
                src=os.path.join(self.build_folder, "man"),
                dst=mandir,
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
