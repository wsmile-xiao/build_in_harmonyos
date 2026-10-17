#!/usr/bin/env python3
"""Conan recipe for qbe 1.2.

qbe is a compiler backend that translates an SSA-form intermediate language
to assembly for amd64 (SysV/Apple), arm64 (Linux/Apple) and rv64.  Upstream
ships a plain POSIX Makefile plus an end-to-end test suite (tools/test.sh)
that emits assembly with qbe, links it with the system C compiler and runs
the produced executables natively.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class QbeConan(ConanFile):
    name = "qbe"
    version = "1.2"
    description = "Compiler backend from SSA intermediate language to amd64/arm64/rv64 assembly"
    license = "MIT"
    homepage = "https://c9x.me/compile/"
    url = "https://c9x.me/compile/"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _c_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("c") or "clang"

    def _sign_binary(self, binary_path):
        if self.settings.os != "OHOS" or not os.path.isfile(binary_path):
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign_tool):
            return
        signed_path = f"{binary_path}.signed"
        self.run(
            f'"{sign_tool}" sign -inFile "{binary_path}" '
            f'-outFile "{signed_path}" -selfSign 1',
            quiet=True,
        )
        if os.path.isfile(signed_path):
            os.replace(signed_path, binary_path)
            os.chmod(binary_path, 0o755)

    def build(self):
        apply_conandata_patches(self)
        compiler = self._c_compiler()
        cflags = "-std=c99 -O2 -g -Wall -Wextra -Wpedantic"
        # qbe builds in-source with a POSIX Makefile; config.h is generated
        # from `uname -m`, so on aarch64 hosts the default target is arm64.
        # SHELL=sh keeps make working on hosts without /bin/sh.
        self.run(
            f'make -j1 SHELL=sh CC="{compiler}" CFLAGS="{cflags}"',
            cwd=self.source_folder,
        )
        self._sign_binary(os.path.join(self.source_folder, "qbe"))
        if can_run(self):
            test_tmp = os.path.join(self.build_folder, "qbe-test-tmp")
            os.makedirs(test_tmp, exist_ok=True)
            # Upstream end-to-end suite (make check): SSA -> assembly -> cc ->
            # native run -> output compare.  tools/test.sh is patched
            # (patches/0001) to honor TMPDIR because HarmonyOS /tmp is
            # read-only.
            self.run(
                f'TMPDIR="{test_tmp}" CC="{compiler}" sh tools/test.sh all',
                cwd=self.source_folder,
            )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "qbe")
        license_dir = os.path.join(self.package_folder, "licenses")
        copy(self, "qbe", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "README", src=self.source_folder, dst=doc_dir, keep_path=False)
        copy(self, "doc/*.txt", src=self.source_folder, dst=doc_dir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=license_dir, keep_path=False)
        self._sign_binary(os.path.join(bin_dir, "qbe"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
