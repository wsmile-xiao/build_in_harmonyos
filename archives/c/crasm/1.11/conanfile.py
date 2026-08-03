#!/usr/bin/env python3
"""Conan recipe for crasm 1.11.

crasm is a portable command-line cross-assembler for 6800, 6502 and Z80 CPUs.
The upstream project uses plain Makefiles and installs a single executable.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CrasmConan(ConanFile):
    name = "crasm"
    version = "1.11"
    description = "Portable cross-assembler for 6800, 6502 and Z80 CPUs"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/crasm/"
    url = "https://sourceforge.net/projects/crasm/"

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

    def _make_args(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        ldflags = []
        if self.settings.os == "OHOS" and os.path.exists("/data/service/hnp/bin/ld.bfd"):
            ldflags.append("-fuse-ld=/data/service/hnp/bin/ld.bfd")
        args = ["SHELL=sh", f'CC="{cc}"']
        if ldflags:
            args.append(f'LDFLAGS="{" ".join(ldflags)}"')
        return " ".join(args)

    def _sign_binary(self, binary_path):
        if self.settings.os != "OHOS" or not os.path.isfile(binary_path):
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool):
            return
        if os.path.isfile(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{binary_path}" 2>/dev/null || true')
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
        make_args = self._make_args()
        self.run(f"make -C src -j1 {make_args}", cwd=self.source_folder)
        self._sign_binary(os.path.join(self.source_folder, "src", "crasm"))
        if can_run(self):
            self.run(f"make -C test -j1 {make_args} test", cwd=self.source_folder)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        license_dir = os.path.join(self.package_folder, "licenses")
        copy(self, "crasm", src=os.path.join(self.source_folder, "src"), dst=bin_dir, keep_path=False)
        copy(self, "crasm.1", src=self.source_folder, dst=man_dir, keep_path=False)
        copy(self, "COPYING", src=self.source_folder, dst=license_dir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=license_dir, keep_path=False)
        self._sign_binary(os.path.join(bin_dir, "crasm"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
