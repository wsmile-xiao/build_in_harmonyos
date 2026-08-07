#!/usr/bin/env python3
"""Conan recipe for acme 0.97-svn20251213 on OHOS aarch64."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AcmeConan(ConanFile):
    name = "acme"
    version = "0.97-svn20251213"
    description = "Multi-platform cross assembler for 6502/6510/65816-family CPUs"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/acme-crossass/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("acme is adapted for OHOS only")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("acme supports OHOS aarch64 only")

    def _sign_binary(self, path):
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

    def build(self):
        apply_conandata_patches(self)
        src_dir = os.path.join(self.source_folder, "src")
        acme_bin = os.path.join(src_dir, "acme")
        compiler = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")

        self.run(f'make CC="{compiler}" -j1', cwd=src_dir)
        self._sign_binary(acme_bin)

        test_path = "{}:/data/service/hnp/bin:$PATH".format(src_dir)
        self.run(f'PATH="{test_path}" make -C testing -j1', cwd=self.source_folder)

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        copy(
            self,
            "acme",
            src=src_dir,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "*.txt",
            src=os.path.join(self.source_folder, "docs"),
            dst=os.path.join(self.package_folder, "share", "doc", "acme"),
            keep_path=False,
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "examples"),
            dst=os.path.join(self.package_folder, "share", "acme", "examples"),
            keep_path=True,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
