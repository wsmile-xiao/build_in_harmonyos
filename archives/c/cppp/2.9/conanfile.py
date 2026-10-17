#!/usr/bin/env python3
"""Conan recipe — cppp 2.9 (partial C/C++ preprocessor).

cppp is a partial preprocessor for C/C++ code. It implements enough of
the C preprocessor to identify preprocessor statements #if, #ifdef, etc.,
and applies their effects for identifiers specified on the command-line.

Build system: plain Makefile (no configure, no autotools).
License:     GPLv2+
Category:    development-tools (CLI utility)

Upstream tests:
  tests/testall (bash, ~14 invocation points).  The harness is a plain
  shell script whose fail() function prints "Unit test failure:" to
  stderr and (deliberately) does NOT exit non-zero — so we must capture
  its full output and count failures ourselves.  It hardcodes
  PROG=${1:-./cppp} so we pass "./cppp" and run from the source root.
"""
import json
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CpppConan(ConanFile):
    name = "cppp"
    version = "2.9"
    description = "Partial preprocessor for C/C++ code"
    license = "GPL-2.0-or-later"
    homepage = "https://www.muppetlabs.com/~breadbox/software/cppp/"
    url = "https://www.muppetlabs.com/~breadbox/pub/software/cppp-2.9.tar.gz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # cppp has a hand-written Makefile; in-source build is simplest.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Nothing to generate: plain Makefile, no configure script.
        pass

    def build(self):
        apply_conandata_patches(self)
        # R33: grab compiler from Conan conf (dict), never rely on bare ${CC}.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Plain make; no configure step. OHOS toybox clang accepts -O2 fine.
        self.run(
            f'make CC="{cc}" -j1',
            cwd=self.source_folder)

        # ── Upstream test suite (bash-based) ──
        # tests/testall drives 11 top-level test groups:
        #   misctests, goodparsingtest ×4 (basic/good/lines/phases),
        #   badparsingtest ×1, trigraphtest ×1, fulltest ×3, numerictest ×1.
        # fail() prints "Unit test failure: ..." to stderr but its `exit 1`
        # is commented out upstream — so the script always exits 0.  We
        # capture the full output and count the failure markers ourselves.
        test_log = os.path.join(self.build_folder, "testall.log")
        self.run(
            'bash ./tests/testall ./cppp > "{}" 2>&1'.format(test_log),
            cwd=self.source_folder)

        discovered = executed = 11
        failed = 0
        if os.path.isfile(test_log):
            with open(test_log, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            failed = content.count("Unit test failure:")
        passed = discovered - failed
        marker = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "make-runtests",
            "command": "bash ./tests/testall ./cppp",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if failed > 0:
            raise ConanException(
                "Upstream test suite reported %d failure(s):" % failed)

    def package(self):
        copy(self, "cppp", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "cppp.1", self.source_folder,
             os.path.join(self.package_folder, "share/man/man1"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share", "licenses"]
