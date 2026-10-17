#!/usr/bin/env python3
"""Conan recipe for jpnevulator 2.3.6 — serial sniffer / hex writer.

Plain Makefile build (CC/CFLAGS via environment).  CLI tool only.

Platform notes:
- Nothing is stripped on install (llvm-strip output is refused by the
  platform's exec policy — yices 2.7.0 evidence + knowledge draft).
- Upstream ships no test suite; verification is carried by the consumer
  test_package (--write hex→binary round-trip against a regular file,
  no real serial device required).
"""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class JpnevulatorConan(ConanFile):
    name = "jpnevulator"
    version = "2.3.6"
    description = ("jpnevulator - serial sniffer: read/display and send "
                   "hexadecimal byte values on a serial line")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/snarlistic/jpnevulator"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]) — conan's
        # get() handles both shapes natively.
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = ""
        env["CC"] = self._cc()
        shell = self._resolve_shell()
        cmd = (f"umask 022; {shlex.quote(shell)} -c "
               f"'make {shlex.quote('jpnevulator')} "
               f"CC={shlex.quote(env['CC'])}' < /dev/null")
        completed = subprocess.run(cmd, shell=True, cwd=self.source_folder,
                                   env=env)
        if completed.returncode != 0:
            raise ConanException(
                f"make failed (rc={completed.returncode})")

    def package(self):
        copy(self, "jpnevulator", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    # ── helpers ─────────────────────────────────────────────────────────

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        if compilers:
            if isinstance(compilers, str):
                import json
                try:
                    compilers = json.loads(compilers)
                except ValueError:
                    compilers = {}
            if compilers.get("c"):
                return compilers["c"]
        return "clang"

    def _resolve_shell(self):
        for candidate in ("/data/service/hnp/bin/bash", "/usr/bin/zsh",
                          "bash", "/bin/sh"):
            if os.path.isfile(candidate):
                return candidate
        return "/bin/sh"
