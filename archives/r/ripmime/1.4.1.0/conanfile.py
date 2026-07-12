#!/usr/bin/env python3
"""Conan recipe for ripmime 1.4.1.0 — Makefile project.

ripmime is a tool to extract attachments from MIME-encoded email.
This recipe uses a plain Makefile build system with HarmonyOS platform adaptations.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RipmimeConan(ConanFile):
    name = "ripmime"
    version = "1.4.1.0"
    description = "Extract attachments from MIME-encoded email"
    license = "BSD-2-Clause"
    homepage = "https://github.com/inflex/ripMIME"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run("make CC=clang -j1")

    def package(self):
        self.run(f"make install DESTDIR={self.package_folder} LOCATION= -j1")
        # HarmonyOS: ELF signing required for binary execution
        bin_path = os.path.join(self.package_folder, "bin", "ripmime")
        if os.path.exists(bin_path):
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            tmp_signed = bin_path + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {bin_path}", quiet=True)
            self.run(f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} -selfSign 1", quiet=True)
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
