#!/usr/bin/env python3
"""Conan recipe — hashchop 0.8-0 (rolling-hash-based data stream chopper).

Build system: plain Makefile (C99, no configure). Upstream default target only
builds test/bench executables, so this recipe compiles hashchop.c directly
into libhashchop (static by default, optional shared) and packages hashchop.h.
The Lua binding (lhashchop.c, optional "lua" target) is not part of the C
library package.
License: ISC
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class HashchopConan(ConanFile):
    name = "hashchop"
    version = "0.8-0"
    description = "Rolling-hash-based data stream chopper (content-defined chunking)"
    license = "ISC"
    homepage = "https://github.com/silentbicycle/hashchop"
    url = "https://github.com/silentbicycle/hashchop"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: resolve toolchain paths from Conan conf, never bare shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or shutil.which("clang") or "clang"
        # OHOS device convention path as last resort (CI workers provide the same layout)
        ar = (comp_execs.get("ar") or shutil.which("llvm-ar")
              or shutil.which("ar") or "/data/service/hnp/bin/llvm-ar")
        src = os.path.join(self.source_folder, "hashchop.c")
        obj = os.path.join(self.build_folder, "hashchop.o")
        # Faithful to upstream Makefile CFLAGS: -std=c99 -Wall -O2 -fPIC
        cflags = "-std=c99 -Wall -O2 -fPIC"
        self.run(f'{cc} {cflags} -c "{src}" -o "{obj}"', cwd=self.build_folder)
        if self.options.shared:
            lib = os.path.join(self.build_folder, "libhashchop.so")
            self.run(f'{cc} -shared -o "{lib}" "{obj}"', cwd=self.build_folder)
        else:
            lib = os.path.join(self.build_folder, "libhashchop.a")
            self.run(f'{ar} rcs "{lib}" "{obj}"', cwd=self.build_folder)

    def package(self):
        copy(self, "hashchop.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libhashchop.*", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["hashchop"]
