#!/usr/bin/env python3
"""Conan recipe — pngcrush 1.8.13 (Makefile, bundled libpng + zlib).

pngcrush is a command-line optimizer for PNG (Portable Network Graphics)
files. It is built as a single statically linked executable from its own
bundled libpng-1.6.32 and zlib-1.2.11 sources, so it has no runtime shared
library dependencies beyond the C library.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PngcrushConan(ConanFile):
    name = "pngcrush"
    version = "1.8.13"
    description = "Optimizer for PNG (Portable Network Graphics) files"
    license = "libpng-2.0"
    homepage = "https://pmt.sourceforge.io/pngcrush/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use the Linux/OHOS tuple
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pngcrush supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Build the static executable from bundled libpng + zlib with the
        # OHOS clang. The Makefile patches out the INTEL_SSE / MIPS_MSA /
        # POWERPC_VSX intrinsics, which are not valid on aarch64.
        self.run("make -f Makefile CC=/data/service/hnp/bin/clang "
                 "LD=/data/service/hnp/bin/clang -j1")

    def package(self):
        copy(self, "pngcrush", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        bin_path = os.path.join(self.package_folder, "bin", "pngcrush")
        os.chmod(bin_path, 0o755)
        # HarmonyOS requires an ELF signature to execute a binary. The signing
        # tools live on the CI worker; where they are absent (local container)
        # the unsigned binary still runs, so the step is guarded rather than
        # made mandatory.
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool) and os.path.exists(objcopy):
            tmp_signed = bin_path + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {bin_path}", quiet=True)
            self.run(
                f"{sign_tool} sign -inFile {bin_path} "
                f"-outFile {tmp_signed} -selfSign 1",
                quiet=True,
            )
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
