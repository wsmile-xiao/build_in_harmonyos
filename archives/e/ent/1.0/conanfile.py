#!/usr/bin/env python3
"""Conan recipe for ent 1.0 — plain Makefile CLI tool."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EntConan(ConanFile):
    name = "ent"
    version = "1.0"
    description = "Pseudorandom number sequence test program"
    license = "Public Domain"
    homepage = "https://www.fourmilab.ch/random/"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Root cause on HarmonyOS PC: upstream Makefile hardcodes gcc, and
        # the default lld path in this environment pulls in a missing
        # libxml2.so.16 dependency. The patch switches to clang and bfd.
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "ent", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        for doc in ["ent.html", "entitle.png"]:
            copy(self, doc, src=self.source_folder, dst=os.path.join(self.package_folder, "share", "ent"), keep_path=False)

        bin_path = os.path.join(self.package_folder, "bin", "ent")
        if os.path.exists(bin_path):
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            tmp_signed = bin_path + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {bin_path} 2>/dev/null || true")
            self.run(f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} -selfSign 1", quiet=True)
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
