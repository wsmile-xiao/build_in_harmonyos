#!/usr/bin/env python3
"""Conan recipe for libaesgm 2013.1.1.

libaesgm (Brian Gladman AES) ships as bare C source files without a
build system. This recipe compiles the sources directly with the Conan
toolchain and packages the static library + headers.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class LibaesgmConan(ConanFile):
    name = "libaesgm"
    version = "2013.1.1"
    description = "Brian Gladman AES (libaesgm) - AES encryption library with block modes"
    license = "BSD-2-Clause"
    homepage = "https://github.com/xmake-mirror/libaesgm"
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

    def _compiler(self):
        # Deterministic compiler selection from settings (R33: no bare
        # shell env var reliance; OHOS/CI profiles use clang or gcc)
        c = str(self.settings.compiler)
        if c in ("clang", "apple-clang"):
            return "clang"
        if c == "gcc":
            return "gcc"
        if c == "msvc":
            return "cl"
        return "cc"

    def _archiver(self):
        c = str(self.settings.compiler)
        if c == "msvc":
            return "lib"
        return "ar"

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler()
        ar = self._archiver()
        sources = ["aes_modes.c", "aescrypt.c", "aeskey.c", "aestab.c"]
        objs = []
        for src in sources:
            obj = src.replace(".c", ".o")
            self.run(f"{cc} -O2 -c {src} -o {obj}", cwd=self.source_folder)
            objs.append(obj)
        if self.options.shared:
            self.run(f"{cc} -shared -o libaesgm.so {' '.join(objs)}", cwd=self.source_folder)
        else:
            self.run(f"{ar} rcs libaesgm.a {' '.join(objs)}", cwd=self.source_folder)

    def package(self):
        copy(self, "*.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"), keep_path=False)
        libdst = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "libaesgm.so*", src=self.source_folder, dst=libdst, keep_path=False)
        else:
            copy(self, "libaesgm.a", src=self.source_folder, dst=libdst, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["aesgm"]
