#!/usr/bin/env python3
"""Conan recipe for zrc 2.7 — UNIX shell and scripting language with
Tcl-like syntax (https://github.com/Edd12321/zrc).

Plain Makefile build (CXX/CXXFLAGS passed on the make command line).
CLI application only; no external dependencies beyond libc/libc++.

Platform notes (OHOS aarch64):
- Upstream CXXFLAGS carry -flto; the override drops it (system-linker
  LTO risk on OHOS) and adds -fsigned-char (AArch64 char is unsigned by
  default; zrc does byte-wise character processing, so restore the
  upstream x86 signed-char semantics).
- Upstream `make install` appends the binary path to /etc/shells and is
  intentionally NOT used; the release binary is packaged directly from
  bin/zrc (same approach as the jpnevulator adaptation).
- Upstream ships no test suite (Makefile only has release/debug/clean
  targets); verification is carried by the consumer test_package, which
  executes real zrc scripts (version probe, -c one-liners, and a
  do/while control-flow script adapted from upstream examples).
- Every build step binds its output to a log file: on this platform
  compiler output handed to conan's inherited stderr stream can be
  silently dropped, so each step redirects `> log 2>&1` and the recipe
  echoes the log tail on failure.
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class ZrcConan(ConanFile):
    name = "zrc"
    version = "2.7"
    description = ("zrc - UNIX shell and scripting language with syntax "
                   "similar to Tcl")
    license = "BSD-2-Clause"
    homepage = "https://github.com/Edd12321/zrc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "zrc requires a POSIX environment")

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]) — conan's
        # get() handles both shapes natively.
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cxx = self._cxx()
        cxxflags = "-std=c++11 -pedantic -Wno-unused-result -fsigned-char"
        self._run_logged(f"make release CXX='{cxx}' CXXFLAGS='{cxxflags}'",
                         "make-release.log")
        if not os.path.isfile(os.path.join(self.source_folder,
                                           "bin", "zrc")):
            raise ConanException("make release finished but bin/zrc is "
                                 "missing; see make-release.log")

    def package(self):
        copy(self, "zrc", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)

    # ── helpers ─────────────────────────────────────────────────────────

    def _cxx(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        if compilers:
            if isinstance(compilers, str):
                import json
                try:
                    compilers = json.loads(compilers)
                except ValueError:
                    compilers = {}
            if compilers.get("cpp"):
                return compilers["cpp"]
        return "clang++"

    def _run_logged(self, cmd, logname):
        """Run cmd in the source folder with output bound to a log file.

        On this platform compiler/make output inherited by conan's
        stderr stream can be silently dropped (and the failure then
        looks like an unexplained exit code), so every step redirects
        into its own log and the tail is echoed on error.
        """
        cwd = self.source_folder
        log = os.path.join(cwd, logname)
        try:
            self.run(f"{cmd} > '{log}' 2>&1", cwd=cwd)
        except ConanException:
            if os.path.isfile(log):
                with open(log, encoding="utf-8", errors="replace") as fh:
                    tail = fh.readlines()[-80:]
                for line in tail:
                    self.output.error(line.rstrip())
            raise
