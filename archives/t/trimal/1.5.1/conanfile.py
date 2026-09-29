#!/usr/bin/env python3
"""Conan recipe for trimal 1.5.1 — trimAl MSA-trimming suite (raw Makefile project).

Upstream: https://github.com/inab/trimal (tag v1.5.1, commit d637091).
Builds the three upstream command-line programs (trimal, readal, statal) from
source/ with the Conan-selected cross toolchain (clang++ -> aarch64-linux-ohos).
Only the platform C++ runtime and libm are linked; no third-party libraries.

Layer-1 upstream tests: the repository ships a dataset regression suite
(scripts/generate_trimmed_msas.sh + scripts/compare_trimmed_msas.sh: 84
dataset alignments x 6 trimming methods = 504 produced MSAs, each diffed
against the reference outputs in dataset/trimmed_msas/). Both scripts are
executed at the end of build().
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TrimalConan(ConanFile):
    name = "trimal"
    version = "1.5.1"
    description = ("trimAl 1.5.1 - automated alignment trimming for phylogenetic "
                   "analyses (CLI programs: trimal, readal, statal)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/inab/trimal"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler must come from the Conan configuration, never from
        # bare shell environment variables (${CC}/${CXX} are empty on workers).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        # R9: always a single job.
        self.run(f"make CC={cxx} -j1", cwd=os.path.join(self.source_folder, "source"))

        # ── upstream dataset regression suite (504 cases) ──
        # Both scripts have no shebang and start ELF binaries, so run them with
        # bash explicitly (OHOS /system/bin/sh cannot execute ELF binaries).
        bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        self.run(f"{bash} scripts/generate_trimmed_msas.sh", cwd=self.source_folder)
        self.run(f"{bash} scripts/compare_trimmed_msas.sh", cwd=self.source_folder)

    def package(self):
        for prog in ("trimal", "readal", "statal"):
            copy(self, prog, src=os.path.join(self.source_folder, "source"),
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
