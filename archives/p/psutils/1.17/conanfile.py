#!/usr/bin/env python3
"""Conan recipe for psutils 1.17."""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class PsutilsConan(ConanFile):
    name = "psutils"
    version = "1.17"
    description = "PostScript document manipulation utilities"
    license = "LicenseRef-PSUtils"
    homepage = "https://github.com/rrthomas/psutils"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _native_bins = ["psbook", "psselect", "pstops", "epsffit", "psnup", "psresize"]

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            if cross_building(self):
                raise ConanInvalidConfiguration(
                    "Cross builds require tools.build:compiler_executables[c]"
                )
            cc = str(self.settings.compiler)
        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        cppflags = f"-std=gnu89 -fPIC {build_type_flags[str(self.settings.build_type)]}"
        self.run(
            f'make CC="{cc}" CPPFLAGS=\'{cppflags}\' '
            'PAPER=a4 PERL=perl OS=UNIX -j1',
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        script_dir = bin_dir
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        include_dir = os.path.join(self.package_folder, "lib", "psutils")
        for path in (bin_dir, man_dir, include_dir):
            os.makedirs(path, exist_ok=True)
        self.run(
            'make install '
            f'BINDIR="{bin_dir}" SCRIPTDIR="{script_dir}" '
            f'MANDIR="{man_dir}" INCLUDEDIR="{include_dir}" '
            'PERL=perl',
            cwd=self.source_folder,
        )
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        for name in self._native_bins:
            self._sign_binary(os.path.join(bin_dir, name))

    def _sign_binary(self, bin_path):
        if not os.path.exists(bin_path):
            return
        os.chmod(bin_path, 0o755)
        if str(self.settings.os) != "OHOS":
            return

        with open(bin_path, "rb") as binary:
            if binary.read(4) != b"\x7fELF":
                raise ConanException(f"Refusing to sign non-ELF file: {bin_path}")

        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        tmp_signed = bin_path + ".signed"
        self.run(f"{objcopy} --remove-section .codesign {bin_path} 2>/dev/null || true")
        self.run(
            f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} -selfSign 1",
            quiet=True,
        )
        os.replace(tmp_signed, bin_path)
        os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share", "lib"]
