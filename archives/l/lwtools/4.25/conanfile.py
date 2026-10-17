#!/usr/bin/env python3
"""Conan recipe for lwtools 4.25 — Motorola 6809 / Hitachi 6309 cross tools.

lwtools is the open tool chain for the 6809/6309 CPUs: assembler (lwasm),
linker (lwlink), object dumper (lwobjdump), archive tool (lwar) and the
experimental C compiler driver (lwcc with its lwcc-cpp / lwcc-cc components).
Upstream ships a plain POSIX Makefile with no configure step:

    * make        — builds $(MAIN_TARGETS): lwasm, lwlink, lwar, lwobjdump,
                    lwcc-cpp
    * make all    — additionally builds $(SECONDARY_TARGETS): lwcc, lwcc-cc
    * make test   — runs test/runtests, a perl driver that executes every
                    script in test/tests and aggregates their "NAME PASS"
                    lines; 4.25 carries one suite, opcodes6809.pl, with 272
                    opcode assertions
    * make install / install-all — needs install(1); installs the programs
                    into $(DESTDIR)$(PREFIX)/bin and the driver components
                    into $(DESTDIR)$(PREFIX)/lib/lwcc/bin

Adaptation notes (HarmonyOS PC, aarch64):
    * W0: no third-party dependencies — ISO C + POSIX, libc only, so
      `requirements()` is intentionally absent.
    * One upstream defect is patched (see patches/): lwcc/cpp-main.c creates
      four of its five global string lists and forgets `sysmacrolist`, so
      process_file() calls lw_stringlist_reset(NULL) and the preprocessor dies
      with SIGSEGV for *any* input file. It is a plain NULL write, identical
      on every platform; upstream's suite only covers lwasm, so 4.25 ships it
      broken and neither `lwcc -E` nor `lwcc -c` can run without the fix.
    * Scope of the C front end is stated honestly: lwcc is experimental and
      lwcc/README.txt declares the direct interface of the compiler and of the
      preprocessor "specifically undefined" (relying on preprocessor output is
      "specifically forbidden"). The test suite therefore asserts only that the
      preprocessor works through the driver and through a direct call, and does
      not claim that lwcc can compile C to usable objects.
    * R33: compiler / archiver come from the Conan conf with an explicit
      llvm-ar / llvm-ranlib fallback, because the OHOS tool chain does not
      guarantee bare `ar` on PATH.
    * PREFIX is handed to make so the driver's baked-in BASEDIR
      ($(PREFIX)/lib/lwcc/, see lwcc/README.txt) matches this package layout.
      PATH is exported as well: the driver only accepts a component when
      access(X_OK) succeeds, and HMDFS does not report the executable bit, in
      which case upstream falls back to a PATH search.
    * package() copies artifacts directly because install(1) is not on the
      CI worker PATH, and ships upstream's COPYING/GPL3 (the recipe declares
      GPL-3.0-or-later).
    * The upstream suite runs in build() and the tail of its log (including the
      "Total: n/n" summary) is echoed to the build log, so a reviewer can read
      the upstream line itself instead of trusting the parsed numbers; a
      non-clean summary aborts the build.
Artifacts: bin/{lwasm,lwlink,lwar,lwobjdump,lwcc,lwcc-cpp,lwcc-cc},
lib/lwcc/bin/{lwcc-cpp,lwcc-cc} and licenses/{COPYING,GPL3}; the software-level
commands.json declares this package as a CLI tool (R38).
License: GPL-3.0-or-later.
"""
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


class LwtoolsConan(ConanFile):
    name = "lwtools"
    version = "4.25"
    description = "Motorola 6809 / Hitachi 6309 交叉开发工具集（汇编器、链接器、归档器、C 编译器驱动）"
    license = "GPL-3.0-or-later"
    homepage = "https://www.lwtools.ca/"
    url = "https://www.lwtools.ca/releases/lwtools/"
    topics = ("6809", "6309", "cross-assembler", "linker", "retrocomputing", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # program -> upstream source subdirectory holding the built binary
    PROGRAM_DIRS = {
        "lwasm": "lwasm",
        "lwlink": "lwlink",
        "lwobjdump": "lwlink",
        "lwar": "lwar",
        "lwcc": "lwcc",
        "lwcc-cpp": "lwcc",
        "lwcc-cc": "lwcc",
    }
    # Programs the driver executes out of $(BASEDIR)/bin at run time.
    DRIVER_COMPONENTS = ("lwcc-cpp", "lwcc-cc")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Plain POSIX Makefile project: build in the source folder.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_tool(self, key, candidates):
        """Build tool from the Conan conf, else from PATH (R33)."""
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get(key)
        if configured:
            return configured
        for candidate in candidates:
            found = shutil.which(candidate)
            if found:
                return found
        raise ConanException(
            "lwtools: no build tool for '{0}' (tried: {1})".format(
                key, ", ".join(candidates)
            )
        )

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException("lwtools requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)

        cc = self._resolve_tool("c", ("clang", "cc"))
        ar = self._resolve_tool("ar", ("ar", "llvm-ar"))
        ranlib = self._resolve_tool("ranlib", ("ranlib", "llvm-ranlib"))
        # R1: only PREFIX is injected (it also fixes the driver's BASEDIR);
        # R9: -j1; `all` pulls in the secondary targets lwcc / lwcc-cc.
        make_vars = 'CC="{0}" AR="{1}" RANLIB="{2}" PREFIX="{3}"'.format(
            cc, ar, ranlib, self.package_folder
        )
        self.run("make -j1 {0} all".format(make_vars), cwd=self.build_folder)

        # ── Upstream regression suite (R51) ──
        # opcodes6809.pl assembles every documented 6809/6309 opcode with
        # ./lwasm/lwasm and compares the emitted bytes against the expected
        # opcode table. It must run from the source root (relative ./lwasm)
        # and needs perl.
        perl = shutil.which("perl")
        if not perl and self.settings.os == "OHOS" and os.path.exists("/data/service/hnp/bin/perl"):
            # HNP-installed perl; only reachable on a HarmonyOS device.
            perl = "/data/service/hnp/bin/perl"
        if not perl:
            raise ConanException(
                "lwtools: the upstream test driver is written in perl, which "
                "the OHOS build environment documents as available "
                "(knowledge/operations/environment.md §2.3) — no interpreter "
                "found on PATH"
            )
        log_path = os.path.join(self.build_folder, "upstream-tests.log")
        self.run(
            '"{0}" test/runtests > upstream-tests.log 2>&1'.format(perl),
            cwd=self.build_folder,
            ignore_errors=True,
        )
        if not os.path.exists(log_path):
            raise ConanException(
                "lwtools upstream suite: no log produced — the runner never executed"
            )
        with open(log_path, "r", errors="replace") as handle:
            log_text = handle.read()
        # Echo the verbatim upstream output: the runner writes it to a file, and
        # a reviewer should not have to trust the parsed numbers alone (R51).
        for line in log_text.splitlines()[-6:]:
            if line.strip():
                self.output.info("upstream-tests.log| " + line)
        summary = re.search(
            r"Total:\s*(\d+)/(\d+)\s*\((\d+) skipped, (\d+) unknown, (\d+) failed\)",
            log_text,
        )
        if not summary:
            raise ConanException(
                "lwtools upstream suite: summary line missing — see "
                "upstream-tests.log\n" + log_text[-800:]
            )
        passed, total, skipped, unknown, failed = (int(g) for g in summary.groups())
        self.output.info(
            "lwtools upstream suite: {0}/{1} opcode assertions passed "
            "(skipped={2} unknown={3} failed={4})".format(passed, total, skipped, unknown, failed)
        )
        if total == 0 or passed != total or skipped or unknown or failed:
            raise ConanException(
                "lwtools upstream suite did not pass cleanly: {0}/{1} "
                "(skipped={2} unknown={3} failed={4})".format(
                    passed, total, skipped, unknown, failed
                )
            )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        driverdir = os.path.join(self.package_folder, "lib", "lwcc", "bin")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(driverdir, exist_ok=True)
        for program, subdir in self.PROGRAM_DIRS.items():
            srcdir = os.path.join(self.build_folder, subdir)
            built = os.path.join(srcdir, program)
            if not os.path.exists(built):
                raise ConanException(
                    "lwtools: build product {0} is missing".format(built)
                )
            copy(self, program, src=srcdir, dst=bindir, keep_path=False)
            os.chmod(os.path.join(bindir, program), 0o755)
        # Upstream `install-all` also stages the driver components under
        # $(PREFIX)/lib/lwcc/bin — replicate it with plain copies.
        for component in self.DRIVER_COMPONENTS:
            copy(self, component, src=bindir, dst=driverdir, keep_path=False)
            os.chmod(os.path.join(driverdir, component), 0o755)
        # The recipe declares GPL-3.0-or-later, so ship upstream's own licence
        # text (COPYING points at GPL3) instead of relying on the declaration.
        licenses_dir = os.path.join(self.package_folder, "licenses")
        for name in ("COPYING", "GPL3"):
            if not os.path.exists(os.path.join(self.build_folder, name)):
                raise ConanException(
                    "lwtools: upstream licence file {0} is missing".format(name)
                )
            copy(self, name, src=self.build_folder, dst=licenses_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
