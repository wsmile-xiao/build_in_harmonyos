#!/usr/bin/env python3
"""Conan recipe for bwa 0.7.19.

BWA is a small C command-line aligner built by a plain Makefile. The package
ships the `bwa` executable only; the internal libbwa.a is a build artifact.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BwaConan(ConanFile):
    name = "bwa"
    version = "0.7.19"
    description = "Burrow-Wheeler Aligner for pairwise alignment of DNA"
    license = "GPL-3.0-or-later AND MIT"
    homepage = "https://github.com/lh3/bwa"
    url = "https://github.com/lh3/bwa"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        self.requires("zlib/1.3.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_tools(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        toolchain_bin = os.path.dirname(cc)
        ar = compilers.get("ar") or (
            os.path.join(toolchain_bin, "llvm-ar") if toolchain_bin else "ar"
        )
        ranlib = compilers.get("ranlib") or (
            os.path.join(toolchain_bin, "llvm-ranlib") if toolchain_bin else "ranlib"
        )
        return cc, ar, ranlib

    def _sign_elf(self, path):
        if str(self.settings.os) != "OHOS" or not os.path.exists(path):
            return

        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.exists(sign_tool):
            os.chmod(path, 0o755)
            return

        signed = path + ".signed"
        if os.path.exists(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" || true',
                     quiet=True)
        self.run(f'"{sign_tool}" sign -inFile "{path}" -outFile "{signed}" '
                 f"-selfSign 1", quiet=True)
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)

        cc, ar, ranlib = self._compiler_tools()
        toolchain_bin = os.path.dirname(cc)
        if toolchain_bin:
            os.environ["PATH"] = toolchain_bin + os.pathsep + os.environ.get("PATH", "")

        zlib_info = self.dependencies["zlib"].cpp_info
        zlib_inc = " ".join(f"-I{d}" for d in zlib_info.includedirs)
        zlib_lib = " ".join(f"-L{d}" for d in zlib_info.libdirs)

        ld_flags = zlib_lib
        if str(self.settings.os) == "OHOS":
            ld_flags = f"{ld_flags} -fuse-ld=/data/service/hnp/bin/ld".strip()

        self.run(
            " ".join(
                [
                    "make -j1",
                    f'CC="{cc}"',
                    f'AR="{ar}"',
                    f'RANLIB="{ranlib}"',
                    f'CPPFLAGS="{zlib_inc}"',
                    f'LDFLAGS="{ld_flags}"',
                    "bwa",
                ]
            ),
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "bwa", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "bwa.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        bin_path = os.path.join(self.package_folder, "bin", "bwa")
        self._sign_elf(bin_path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
