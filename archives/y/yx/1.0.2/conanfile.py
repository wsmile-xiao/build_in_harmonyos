#!/usr/bin/env python3
"""Conan recipe — yx 1.0.2 (Makefile / single-file C CLI tool).

yx ("YAML Data Extraction Tool") is a small command-line utility that
extracts targeted data from a YAML document along a key / sequence-index path.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class YxConan(ConanFile):
    name = "yx"
    version = "1.0.2"
    description = "YAML Data Extraction Tool - extract targeted data from YAML documents"
    license = "MIT"
    homepage = "https://gitlab.com/tomalok/yx"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # CLI executable, not a library (R38: commands.json at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libyaml/0.2.5")

    def validate(self):
        # R32: OHOS must be matched alongside Linux
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yx supports Linux/OHOS only, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cc = self._c_compiler()

        # Dependency include / library dirs (libyaml is a static library here).
        dep = self.dependencies["libyaml"].cpp_info
        incdirs = " ".join(f"-I{d}" for d in dep.includedirs)
        libdirs = " ".join(f"-L{d}" for d in dep.libdirs)

        # The upstream Makefile hard-codes the compiler in its only rule
        # ("cc -Os -o yx yx.c -lyaml") and exposes no CC/CFLAGS/LDFLAGS hook,
        # while OHOS provides no "cc" in PATH.  Reproduce the exact upstream
        # compile rule with the profile-selected compiler and the libyaml
        # dependency flags.
        self.run(f"{cc} -Os -o yx yx.c {incdirs} {libdirs} -lyaml",
                 cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Upstream "make install" uses "install -sDm0755 -t <dir>", which the
        # OHOS toybox "install" cannot parse (-D/-t unsupported).  Reproduce the
        # same install logic here: create the dirs, copy and chmod 0755.
        # NOTE: the "-s" (strip) part is intentionally NOT reproduced — on OHOS
        # every ELF carries a `.codesign` section and any rewrite of the file
        # (llvm-strip / llvm-objcopy / append) invalidates that signature, after
        # which the kernel refuses to exec it (E077).  The toolchain-signed
        # binary is installed verbatim.
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "yx", src=self.source_folder, dst=bin_dir)
        copy(self, "yx.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

        binary = os.path.join(bin_dir, "yx")
        if os.path.exists(binary):
            os.chmod(binary, 0o755)  # install -m0755

    def package_info(self):
        # Standalone binary — no library to link, only a bin/ directory.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _c_compiler(self):
        # R33: read the compiler from the Conan profile, never from bare ${CC}.
        conf = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        return conf.get("c", "clang")
