#!/usr/bin/env python3
"""Conan recipe — sljit 0.0-git20260924.b706c11 (stack-less JIT compiler, GNU Makefile).

Upstream zherczeg/sljit at b706c11ca471c3da773ee595164acb6efd2c5574 (2026-09-24).
Build system: plain GNUmakefile (no configure, no install rules). The recipe
compiles sljit_src/sljitLir.c into libsljit.a (and libsljit.so when
shared=True), installs the public headers, and runs the two upstream test
binaries defined by GNUmakefile TARGET (bin/sljit_test, bin/regex_test).
"""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SljitConan(ConanFile):
    name = "sljit"
    version = "0.0-git20260924.b706c11"
    description = (
        "Stack-less platform independent JIT compiler "
        "(platform independent assembler / LIR code generator backend)"
    )
    license = "BSD-2-Clause"
    homepage = "https://github.com/zherczeg/sljit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_cc(self):
        try:
            conf_cc = self.conf.get("tools.build:compiler_executables:c", check_type=str)
        except Exception:
            conf_cc = None
        if conf_cc and os.path.isfile(conf_cc):
            return conf_cc
        return conf_cc or "clang"

    def _resolve_ar(self):
        try:
            conf_ar = self.conf.get("tools.build:compiler_executables:ar", check_type=str)
        except Exception:
            conf_ar = None
        return conf_ar or "llvm-ar"

    def _resolve_ranlib(self):
        try:
            conf_ranlib = self.conf.get("tools.build:compiler_executables:ranlib", check_type=str)
        except Exception:
            conf_ranlib = None
        return conf_ranlib or "llvm-ranlib"

    def _resolve_make(self):
        make_env = os.environ.get("HMBS_MAKE", "")
        if make_env and os.path.isfile(make_env):
            return make_env
        return "make"

    def build(self):
        cc = self._resolve_cc()
        ar = self._resolve_ar()
        ranlib = self._resolve_ranlib()
        make = self._resolve_make()
        self.output.info("sljit build: CC=%s AR=%s RANLIB=%s MAKE=%s" % (cc, ar, ranlib, make))

        # --- Compile the library object (single TU: sljitLir.c pulls in the
        # --- native backends + exec allocators internally, same as GNUmakefile).
        cflags = "-O2 -fPIC -Wall -Isljit_src"
        if self.settings.build_type == "Debug":
            cflags = "-O0 -g -fPIC -Wall -Isljit_src"
        self.run(
            '"%s" %s -c sljit_src/sljitLir.c -o sljitLir.o' % (cc, cflags),
            cwd=self.source_folder,
        )
        self.run('"%s" rcs libsljit.a sljitLir.o' % ar, cwd=self.source_folder)
        self.run('"%s" libsljit.a' % ranlib, cwd=self.source_folder)
        if self.options.shared:
            self.run(
                '"%s" -shared -fPIC -o libsljit.so sljitLir.o -lm -lpthread' % cc,
                cwd=self.source_folder,
            )

        self._run_upstream_tests(cc, make)

    # ------------------------------------------------------------------
    # Upstream test suite: GNUmakefile TARGET = bin/sljit_test bin/regex_test.
    # Each binary is one registered test entry (discovered=2). sljit_test
    # runs 138 internal LIR cases and returns TEST_COUNT-successful_tests;
    # regex_test runs the regex JIT cases and prints its own summary.
    # Single deterministic source per binary: its log file + exit code.
    # ------------------------------------------------------------------
    def _strip_ansi(self, text):
        # Upstream prints colorized summaries on non-Windows hosts, e.g.
        # 'all tests \x1b[32mPASSED\x1b[0m' (COLOR_GREEN/COLOR_DEFAULT in
        # test_src/sljitTest.c and regex_src/regexMain.c). Strip CSI
        # sequences before verdict matching so the literal
        # 'all tests PASSED' is visible. Single deterministic source:
        # the per-binary log file content.
        return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)

    def _run_upstream_tests(self, cc, make):
        # Build both upstream binaries with the Conan compiler (R33: CC as
        # make command-line override, never bare ${CC}).
        self.run(
            '%s -j1 CC="%s" CFLAGS="-O2 -fPIC -Wall"' % (make, cc),
            cwd=self.source_folder,
        )
        cases = [
            ("bin/sljit_test", "SLJIT tests:"),
            ("bin/regex_test", "REGEX tests:"),
        ]
        passed = 0
        failed = 0
        for binary, summary_tag in cases:
            bin_path = os.path.join(self.source_folder, binary)
            try:
                size = os.path.getsize(bin_path)
            except OSError:
                raise ConanException("sljit upstream binary missing: %s" % bin_path)
            if size == 0:
                raise ConanException("sljit upstream binary empty: %s" % bin_path)
            log_path = os.path.join(
                self.build_folder, os.path.basename(binary) + ".log"
            )
            try:
                self.run('"%s" > "%s" 2>&1' % (bin_path, log_path), cwd=self.source_folder)
                rc = 0
            except ConanException:
                rc = 1
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                    out = handle.read()
            except OSError:
                out = ""
            self.output.info("upstream %s output:\n%s" % (binary, out[-3000:]))
            # One deterministic verdict per binary: exit 0 AND the summary
            # line present AND the green marker present AND no failure marker.
            # No stdout word counting, no arithmetic fixups. Verdict runs on
            # ANSI-stripped log text (upstream colorizes PASSED/FAILED).
            clean = self._strip_ansi(out)
            ok = (
                rc == 0
                and clean.strip() != ""
                and summary_tag in clean
                and "all tests PASSED" in clean
                and "FAILED" not in clean
                and "FAIL " not in clean
                and "FAIL:" not in clean
            )
            if ok:
                passed += 1
                self.output.info("sljit upstream case passed: %s" % binary)
            else:
                failed += 1
                self.output.error(
                    "sljit upstream case failed: %s (rc=%s)" % (binary, rc)
                )

        discovered = 2
        executed = 2
        if passed + failed != executed:
            raise ConanException(
                "sljit upstream parse bug: passed(%d)+failed(%d)!=executed(%d)"
                % (passed, failed, executed)
            )
        if executed != discovered:
            raise ConanException(
                "sljit upstream parse bug: executed(%d)!=discovered(%d)"
                % (executed, discovered)
            )
        upstream = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "make",
            "command": "make -j1 CC=<Conan compiler> && ./bin/sljit_test && ./bin/regex_test",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        if failed > 0:
            upstream["gaps"] = [
                {
                    "count": failed,
                    "category": "test_failure",
                    "detail": "upstream GNUmakefile test binary reported failure; "
                              "see bin/sljit_test.log and bin/regex_test.log",
                    "evidence": "build folder sljit_test.log / regex_test.log "
                                "summary lines (SLJIT tests: / REGEX tests:)",
                }
            ]
        summary_path = os.path.join(self.build_folder, "upstream_test_summary.json")
        with open(summary_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(upstream, handle, ensure_ascii=False, indent=2)
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        self.output.info(line)
        print(line, flush=True)
        if failed > 0:
            raise ConanException(
                "sljit upstream tests failed: %s" % json.dumps(upstream, ensure_ascii=False)
            )

    def package(self):
        copy(
            self,
            "sljitLir.h",
            src=os.path.join(self.source_folder, "sljit_src"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "sljitConfig.h",
            src=os.path.join(self.source_folder, "sljit_src"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "sljitConfigCPU.h",
            src=os.path.join(self.source_folder, "sljit_src"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "sljitConfigInternal.h",
            src=os.path.join(self.source_folder, "sljit_src"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "libsljit.a",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        if self.options.shared:
            copy(
                self,
                "libsljit.so",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        summary_src = os.path.join(self.build_folder, "upstream_test_summary.json")
        if os.path.isfile(summary_src):
            copy(
                self,
                "upstream_test_summary.json",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "res"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = ["sljit"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.extend(["m", "pthread"])
