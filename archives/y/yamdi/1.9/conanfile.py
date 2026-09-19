#!/usr/bin/env python3
"""Conan recipe for yamdi 1.9 — Yet Another Metadata Injector for FLV.

yamdi (ioppermann/yamdi) is a single-file C program (yamdi.c, ~2400
lines) that injects onMetaData metadata into FLV video files.  Zero
external dependencies; the upstream Makefile hardcodes gcc and its
install rule assumes root + /usr/local, so the recipe compiles the
single translation unit directly with the profile compiler instead.

Platform notes:
- LD_LIBRARY_PATH is explicitly emptied during build: some CI workers
  carry an ambient LD pointing at /usr/local/lib whose incompatible
  libxml2.so.16 breaks the SDK's lld on every link (CI-021 build
  #48068 — mechanism documented in libodfgen/libabw).
- Upstream has no test suite (single-source tool, no tests/ anywhere),
  so verification lives in test_package (metadata-injection roundtrip
  on a minimal FLV fixture + negative-path assertions).
"""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class YamdiConan(ConanFile):
    name = "yamdi"
    version = "1.9"
    description = ("yamdi - Yet Another Metadata Injector for FLV: "
                   "injects onMetaData (duration, keyframes, ...) into "
                   "FLV video files")
    license = "BSD-3-Clause"
    homepage = "https://github.com/ioppermann/yamdi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]) — conan's
        # get() handles both shapes natively.
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Upstream Makefile hardcodes gcc; compile with the profile
        # compiler instead.  LD_LIBRARY_PATH shield — see docstring.
        cc = self._cc()
        shield = Environment()
        shield.define("LD_LIBRARY_PATH", "")
        with shield.vars(self).apply():
            cmd = (f"{shlex.quote(cc)} -O2 -Wall -fPIC "
                   f"yamdi.c -o yamdi < /dev/null")
            completed = subprocess.run(cmd, shell=True,
                                       cwd=self.source_folder)
            if completed.returncode != 0:
                raise ConanException(
                    f"compile failed (rc={completed.returncode})")

    def package(self):
        copy(self, "yamdi", src=self.source_folder,
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
