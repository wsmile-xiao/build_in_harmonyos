#!/usr/bin/env python3
"""Conan recipe for yank 1.3.0 — yank terminal output to clipboard.

yank (mptre/yank) is a single-file C tool: read stdin, select a line
(interactively or with -l), and hand it to a clipboard command.
Upstream Makefile is BSD make (uses ${.CURDIR}) and its install rule
strips via `install -s` — both unusable here (GNU make can't parse it;
strip output is refused by the platform's exec policy — yices 2.7.0
evidence), so the recipe compiles yank.c directly.

Platform notes:
- LD_LIBRARY_PATH is explicitly emptied during build (lld/libxml2
  shield — CI-021 build #48068, mechanism in libodfgen/libabw).
- YANKCMD default (xsel) does not exist on this platform; it only
  matters for invocations without an explicit command.
- Upstream has no test suite (single-source tool); verification lives
  in test_package (-l non-interactive mode + -v probe).
"""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class YankConan(ConanFile):
    name = "yank"
    version = "1.3.0"
    description = ("yank - yank terminal output to clipboard: select "
                   "lines from stdin and pass them to a command")
    license = "ISC"
    homepage = "https://github.com/mptre/yank"
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
        # Upstream Makefile is BSD make + `install -s`; compile directly
        # instead.  LD_LIBRARY_PATH shield — see docstring.
        cc = self._cc()
        shield = Environment()
        shield.define("LD_LIBRARY_PATH", "")
        with shield.vars(self).apply():
            cmd = (f"{shlex.quote(cc)} -O2 -Wall "
                   f'-DVERSION=\\"{self.version}\\" '
                   f'-DYANKCMD=\\"xsel\\" '
                   f"yank.c -o yank < /dev/null")
            completed = subprocess.run(cmd, shell=True,
                                       cwd=self.source_folder)
            if completed.returncode != 0:
                raise ConanException(
                    f"compile failed (rc={completed.returncode})")

    def package(self):
        copy(self, "yank", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

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
