#!/usr/bin/env python3
"""Conan recipe for giflib 5.2.2 (Makefile)."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class GiflibConan(ConanFile):
    name = "giflib"
    version = "5.2.2"
    description = "GIF image encoding and decoding library"
    license = "MIT"
    homepage = "https://sourceforge.net/projects/giflib/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="giflib-5.2.2.tar.gz",
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c") or "clang"
        ar = executables.get("ar") or self._tool_next_to(cc, "llvm-ar") or "llvm-ar"
        optimization = "-O0 -g" if str(self.settings.build_type) == "Debug" else "-O2"
        cflags = f"-std=gnu99 -fPIC {optimization}"
        targets = [
            "libgif.a",
            "libutil.a",
            "gif2rgb",
            "gifbuild",
            "giffix",
            "giftext",
            "giftool",
            "gifclrmp",
            "gifbg",
            "gifcolor",
            "gifecho",
            "giffilter",
            "gifhisto",
            "gifinto",
            "gifsponge",
            "gifwedge",
        ]
        if self.options.shared:
            targets.insert(0, "libgif.so")
        self.run(
            "make -j1 "
            f"CC={shlex.quote(cc)} AR={shlex.quote(ar)} "
            f"CFLAGS={shlex.quote(cflags)} {' '.join(targets)}",
            cwd=self.source_folder,
        )
        self.run("make -C tests", cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "gif_lib.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        if self.options.shared:
            built_library = os.path.join(self.source_folder, "libgif.so")
            for filename in ("libgif.so", "libgif.so.7", "libgif.so.7.2.0"):
                shutil.copy2(built_library, os.path.join(libdir, filename))
        else:
            copy(
                self,
                "libgif.a",
                src=self.source_folder,
                dst=libdir,
                keep_path=False,
            )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["gif"]
        self.cpp_info.set_property("cmake_file_name", "giflib")
        self.cpp_info.set_property("cmake_target_name", "giflib::giflib")
        self.cpp_info.set_property("pkg_config_name", "giflib")

    @staticmethod
    def _tool_next_to(compiler, tool):
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        candidate = os.path.join(bindir, tool) if bindir else ""
        return candidate if candidate and os.path.isfile(candidate) else ""
