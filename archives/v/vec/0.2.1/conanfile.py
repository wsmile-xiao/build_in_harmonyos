#!/usr/bin/env python3
"""Conan recipe — vec 0.2.1

Type-safe dynamic array (vector) implementation for C, by rxi.
Upstream is a drop-in source pair (src/vec.c + src/vec.h) with no
configure/make/cmake build system, so the recipe compiles vec.c into a
static library directly with the toolchain compiler from Conan conf (R33)
and installs vec.h alongside libvec.a.
License: MIT
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class VecConan(ConanFile):
    name = "vec"
    version = "0.2.1"
    description = "A type-safe dynamic array implementation for C"
    license = "MIT"
    homepage = "https://github.com/rxi/vec"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        src_dir = os.path.join(self.source_folder, "src")
        self.run(
            f'"{cc}" -c -O2 -fPIC -I"{src_dir}" '
            f'"{os.path.join(src_dir, "vec.c")}" -o "{os.path.join(self.build_folder, "vec.o")}"'
        )
        self.run(f'"{ar}" rcs "{os.path.join(self.build_folder, "libvec.a")}" vec.o',
                 cwd=self.build_folder)

    def package(self):
        copy(self, "vec.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libvec.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["vec"]
