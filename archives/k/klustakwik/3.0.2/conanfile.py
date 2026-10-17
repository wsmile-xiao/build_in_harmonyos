#!/usr/bin/env python3
"""Conan recipe for klustakwik 3.0.2 — Masked KlustaKwik spike-sorting clusterer.

klustakwik is a plain-Makefile C++ project (no autotools/cmake/meson, no
external dependencies). It compiles the `KlustaKwik` CLI executable, which
clusters spike waveform data (fet/mask files) into a mixture of Gaussians
using the CEM algorithm with masks.

HarmonyOS adaptation notes:
- The upstream Makefile hard-codes `CC = g++` and builds with `-O3 -ffast-math`.
  On OHOS the compiler comes from the Conan toolchain conf (clang/clang++),
  so CC is overridden from `tools.build:compiler_executables` (R33).
- The resulting ELF must be code-signed with the HNP binary-sign-tool on OHOS,
  otherwise the HarmonyOS kernel refuses to exec it. The sign tool exists only
  on the OHOS CI worker, so signing is attempted only when the tool is present
  (the local macOS verify run skips it).
- Upstream ships no tests (only author reference logs expected_output*.txt);
  test_package therefore runs a real clustering job on synthetic data and
  checks the .clu output, plus an OHOS-specific ELF/arch check.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class KlustakwikConan(ConanFile):
    name = "klustakwik"
    version = "3.0.2"
    description = "Fast clustering of spike waveform data into a mixture of Gaussians (Masked KlustaKwik)"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/klustakwik/"
    url = "https://sourceforge.net/projects/klustakwik/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # SourceForge download URLs end with /download, so the fetched file has
        # no extension and conan would try to unzip it as a zip. The upstream
        # artifact is actually a tar.bz2 archive (KlustaKwik-3.0.2.bz2), so the
        # explicit filename lets conan detect the format and untar correctly.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="KlustaKwik-3.0.2.tar.bz2")

    def _sign_elf(self, path):
        """ELF code-sign a file so the HarmonyOS kernel can exec it."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool) and os.path.exists(path):
            # Remove any stale .codesign section first, then self-sign
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # chmod may be unsupported on the device FS (HMBS_CAP_CHMOD=0)

    def build(self):
        apply_conandata_patches(self)

        # R33: get the compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "c++") if compilers else "c++"
        # The upstream Makefile uses $(CC) to compile .cpp files (C++), so the
        # C++ compiler is passed through the CC variable.
        self.run(f'make CC="{cxx}" -j1', cwd=self.source_folder)

        if self.settings.os == "OHOS":
            self._sign_elf(os.path.join(self.source_folder, "KlustaKwik"))

    def package(self):
        copy(self, "KlustaKwik", self.source_folder, os.path.join(self.package_folder, "bin"))
        try:
            os.chmod(os.path.join(self.package_folder, "bin", "KlustaKwik"), 0o755)
        except OSError:
            pass  # chmod may be unsupported on the device FS (HMBS_CAP_CHMOD=0)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
