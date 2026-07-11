#!/usr/bin/env python3
"""Conan recipe — lz4 1.10.0 (fast compression library + CLI tool).

Build system: pure Makefile (no configure script).
R38: includes lz4 CLI tool → commands.json required.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Lz4Conan(ConanFile):
    name = "lz4"
    version = "1.10.0"
    description = "Fast compression library and CLI tool"
    license = "BSD-2-Clause"
    homepage = "https://github.com/lz4/lz4"
    url = ""  # CI fills this

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
        # lz4 uses pure Makefile — build both lib and programs
        # POSIX_ENV=Yes: OHOS not in default POSIX_ENV check (patch adds it,
        # but pass explicitly for safety)
        # Run in source_folder — lz4 Makefile is in the root source dir
        self.run("make -j1 POSIX_ENV=Yes", cwd=self.source_folder)
        if self.options.shared:
            self.run("make -j1 POSIX_ENV=Yes lib-shared", cwd=self.source_folder)

    def package(self):
        # Use copy() instead of make install — HarmonyOS lacks install(1)
        copy(self, "lz4.h", src=self.source_folder + "/lib",
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "lz4hc.h", src=self.source_folder + "/lib",
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "lz4frame.h", src=self.source_folder + "/lib",
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "lz4frame_static.h", src=self.source_folder + "/lib",
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "lz4file.h", src=self.source_folder + "/lib",
             dst=os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "liblz4.so*", src=self.source_folder + "/lib",
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        else:
            copy(self, "liblz4.a", src=self.source_folder + "/lib",
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # CLI tool (R38)
        copy(self, "lz4", src=self.source_folder + "/programs",
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["lz4"]
        self.cpp_info.bindirs = ["bin"]
