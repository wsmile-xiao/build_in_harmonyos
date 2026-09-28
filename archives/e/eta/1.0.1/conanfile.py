#!/usr/bin/env python3
"""Conan recipe for eta 1.0.1 — progress/ETA monitor for shell pipelines.

eta (https://github.com/aioobe/eta) is a small C application: it runs a
progress command repeatedly, extracts the first number from its output and
prints a progress bar with an estimated time to completion. Build is a plain
Makefile with no configure step.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class EtaConan(ConanFile):
    name = "eta"
    version = "1.0.1"
    description = "Generic tool for monitoring ETA and progress of an arbitrary process"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/aioobe/eta"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    _source_url = "https://github.com/aioobe/eta/archive/refs/tags/v1.0.1.tar.gz"
    _source_sha256 = "ccd41559dc12527d925ef32e22cd2c1e79428f3ec7a620ac9a74ed6be028d2e6"

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("eta is adapted for OHOS only")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("eta supports OHOS aarch64 only")

    def layout(self):
        basic_layout(self)

    def source(self):
        # URL and SHA256 live in the recipe on purpose: the CI pre-download
        # branch parses conandata.yml and fails on an unset BUILD_DIR before
        # Conan runs. Keeping the recipe self-contained avoids that path.
        get(
            self,
            url=self._source_url,
            sha256=self._source_sha256,
            strip_root=True,
        )

    def build(self):
        # POSIX declares WEXITSTATUS in <sys/wait.h>. Upstream relies on
        # glibc and the OHOS musl sysroot exposing it transitively through
        # <stdlib.h>; vanilla musl does not, so include the owning header
        # directly instead of depending on a libc-specific quirk.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "eta.c"),
            "#include <stdio.h>",
            "#include <stdio.h>\n#include <sys/wait.h>",
        )

        # R33: take the compiler from Conan conf, never from shell env vars.
        # The upstream Makefile hardcodes CC = gcc; a command-line assignment
        # overrides it, and the OHOS cross command carries --target/--sysroot.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"

        # R9: single job.
        self.run(f'make CC="{cc}" -j1', cwd=self.source_folder)

        self._sign_binary(os.path.join(self.source_folder, "eta"))

    def _sign_binary(self, path):
        # OHOS refuses to execute unsigned ELF binaries. Same signing helper
        # as other application packages; skipped when the tool is absent
        # (e.g. non-OHOS or host builds without the device service).
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if self.settings.os != "OHOS" or not os.path.exists(sign_tool):
            return
        tmp_signed = path + ".signed"
        self.run(f"{objcopy} --remove-section .codesign {path} 2>/dev/null || true")
        self.run(
            f"{sign_tool} sign -inFile {path} -outFile {tmp_signed} -selfSign 1",
            quiet=True,
        )
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)

    def package(self):
        copy(
            self,
            "eta",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "eta.1",
            src=os.path.join(self.source_folder, "docs"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "eta", "doc"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
