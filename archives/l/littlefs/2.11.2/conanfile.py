#!/usr/bin/env python3
"""Conan recipe — littlefs 2.11.2 (embedded filesystem library).

Build system: pure Makefile (no CMake/configure).  Only the static
library target liblfs.a is built (the upstream Makefile builds liblfs.a
by default when no test.c/main.c exists in the source root).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LittlefsConan(ConanFile):
    name = "littlefs"
    version = "2.11.2"
    description = "A little fail-safe filesystem designed for microcontrollers"
    license = "BSD-3-Clause"
    homepage = "https://github.com/littlefs-project/littlefs"
    url = "https://github.com/littlefs-project/littlefs"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler/ar come from the Conan profile conf, not bare env vars
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = "llvm-ar"
        kwargs = {"cwd": self.source_folder}
        self.run(f"make -j1 CC={cc} AR={ar}", **kwargs)
        if self.options.shared:
            # littlefs upstream has no shared-lib target in the Makefile;
            # reject shared builds up front instead of silently producing .a
            raise ConanException(
                "littlefs upstream Makefile does not provide a shared-library "
                "target; use shared=False")

    def package(self):
        copy(self, "liblfs.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "lfs.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "lfs_util.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["lfs"]