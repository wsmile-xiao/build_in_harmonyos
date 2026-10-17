#!/usr/bin/env python3
"""Conan recipe for astronomy 2.1.9 (Astronomy Engine, single-file C library).

Upstream ships a single translation unit (source/c/astronomy.c + astronomy.h);
there is no upstream build system for the C library itself. This recipe
compiles astronomy.c into a static library and installs the public header,
preserving the upstream source behavior.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AstronomyConan(ConanFile):
    name = "astronomy"
    version = "2.1.9"
    description = "Astronomy Engine: multi-language calculation of sun, moon, and planet positions"
    license = "MIT"
    homepage = "https://github.com/cosinekitty/astronomy"
    url = ""  # CI fills this

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = (
            compilers.get("c")
            or os.environ.get("CC")
            or shutil.which("clang")
            or shutil.which("cc")
            or "cc"
        )
        ar = (
            compilers.get("ar")
            or shutil.which("llvm-ar")
            or shutil.which("ar")
            or "ar"
        )
        src_dir = os.path.join(self.source_folder, "source", "c")
        # 上游 demo/c/build 使用 -O3；保持源码行为，添加 -fPIC 以支持共享链接
        cflags = "-O2 -fPIC"
        self.run(f"{cc} {cflags} -c astronomy.c -o astronomy.o", cwd=src_dir)
        self.run(f"{ar} rcs libastronomy.a astronomy.o", cwd=src_dir)

    def package(self):
        src_dir = os.path.join(self.source_folder, "source", "c")
        copy(self, "astronomy.h", src=src_dir, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libastronomy.a", src=src_dir, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["astronomy"]
