#!/usr/bin/env python3
"""Conan recipe for gti 1.9.1.1, packaging upstream gti 1.9.1."""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class GtiConan(ConanFile):
    name = "gti"
    version = "1.9.1.1"
    description = "ASCII-art typo-correcting launcher for git commands"
    license = "MIT"
    homepage = "https://github.com/rwos/gti"
    url = "https://github.com/rwos/gti"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        default_cc = {
            "gcc": "gcc",
            "clang": "clang",
        }.get(str(self.settings.compiler), "cc")
        cc = compilers.get("c", default_cc)
        shell = (
            "/data/service/hnp/bin/bash"
            if str(self.settings.os) == "OHOS"
            else "/bin/sh"
        )
        if not os.path.isfile(shell):
            raise ConanException(f"Required build shell not found: {shell}")
        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        warning_flags = (
            "-std=c89 -Wpedantic -Wall -Wextra -Wunused -Wshadow "
            "-Wdouble-promotion -Wstrict-overflow=5"
        )
        cflags = (
            f"{build_type_flags.get(str(self.settings.build_type), '-O2 -DNDEBUG')} "
            f"{warning_flags}"
        )
        subprocess.run(
            ["make", f"CC={cc}", f"CFLAGS={cflags}", "STRIP=true", f"SHELL={shell}", "-j1"],
            cwd=self.source_folder,
            check=True,
        )

    def package(self):
        copy(self, "gti", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "gti.6", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man6"), keep_path=False)
        copy(self, "gti.bash", src=os.path.join(self.source_folder, "completions"),
             dst=os.path.join(self.package_folder, "share", "bash-completion", "completions"),
             keep_path=False)
        zsh_completion_dir = os.path.join(
            self.package_folder, "share", "zsh", "site-functions"
        )
        copy(self, "gti.zsh", src=os.path.join(self.source_folder, "completions"),
             dst=zsh_completion_dir, keep_path=False)
        os.replace(
            os.path.join(zsh_completion_dir, "gti.zsh"),
            os.path.join(zsh_completion_dir, "_gti"),
        )
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        bin_path = os.path.join(self.package_folder, "bin", "gti")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)
        if os.path.exists(bin_path) and str(self.settings.os) == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            tmp_signed = bin_path + ".signed"
            subprocess.run(
                [sign_tool, "sign", "-inFile", bin_path, "-outFile", tmp_signed, "-selfSign", "1"],
                check=True,
            )
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
