#!/usr/bin/env python3
"""Conan recipe for mklittlefs 4.1.0 — LittleFS image builder tool.

Build system: GNU Makefile. The official release zip is self-contained:
it bundles littlefs v2.11.1 (commit 8e251dd675da00342d45dac78b6f627f119aed03)
and the tclap headers, so there are no external dependencies and no
submodule handling at build time.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MklittlefsConan(ConanFile):
    name = "mklittlefs"
    version = "4.1.0"
    description = "LittleFS filesystem image creation tool (create/list/unpack)"
    license = "MIT"
    homepage = "https://github.com/earlephilhower/mklittlefs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # No strip_root: the release zip has no single top-level folder
        # (Makefile, main.cpp, littlefs/, tclap/ all at the archive root).
        get(self, **self.conan_data["sources"][self.version])
        apply_conandata_patches(self)

    def _existing(self, path):
        """Return path if it is an executable file, else None."""
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
        return None

    def build(self):
        # R33: compiler from Conan conf, never from shell env vars.
        # The compiler configured in the CI profile may not exist on the
        # current executor; fall back to PATH lookup then plain name.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = self._existing(compilers.get("c")) or shutil.which("clang") or "clang"
        cxx = self._existing(compilers.get("cpp")) or shutil.which("clang++") or "clang++"

        # VERSION/LITTLEFS_VERSION: the Makefile derives them from
        # `git describe`; the source zip has no usable git checkout, and
        # LITTLEFS_VERSION uses `:=` so it must be passed on the make
        # command line (not the environment) to take effect.
        # STRIP=true: strip would drop the .codesign section and leave the
        # binary unusable (Operation not permitted) on OHOS.
        # -Wno-error=unused-command-line-argument: the OHOS clang wrapper
        # injects -Wl,--code-sign, which trips -Werror otherwise.
        # R9: -j1
        self.run(
            "make -C {} CC={} CXX={} VERSION={} LITTLEFS_VERSION=v2.11.1 "
            "CFLAGS='-Wno-error=unused-command-line-argument' "
            "CXXFLAGS='-Wno-error=unused-command-line-argument' "
            "STRIP=true -j1".format(self.source_folder, cc, cxx, self.version)
        )

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "mklittlefs", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
