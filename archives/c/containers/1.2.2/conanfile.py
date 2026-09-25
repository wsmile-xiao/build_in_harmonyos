#!/usr/bin/env python3
"""Conan recipe — containers 1.2.2 (raw Makefile C library, no configure).

Upstream build: make static_clang / dynamic_clang (clang only). Headers live
in src/include/*.h plus an amalgamated containers.h at repo root.
OHOS AArch64 char is unsigned by default; the AVL/set internals store balance
factors (-1/0/1) in char, so -fsigned-char is required (verified: without it
upstream tst/test_set.c assertion fails). -Wno-tautological-constant-out-of-
range-compare silences a clang-only diagnostic that gcc never raised.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class ContainersConan(ConanFile):
    name = "containers"
    version = "1.2.2"
    description = "C89 container library (array/vector/deque/list/map/set/stack/queue) by bkthomps"
    license = "MIT"
    homepage = "https://github.com/bkthomps/Containers"
    url = "https://github.com/bkthomps/Containers"

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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler flags come from Conan conf, never bare shell env vars.
        # Conan 2.29: tools.build:compiler_executables is a dict conf; the
        # ":c" sub-key is not a standalone conf key (2048.c recipe pattern).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        cflags = "-O3 -fPIC -fsigned-char -Wno-tautological-constant-out-of-range-compare"
        if self.options.shared:
            self.run(f"{cc} -shared -o containers.so {cflags} src/*.c",
                     cwd=self.source_folder)
        else:
            self.run(f"{cc} src/*.c -c {cflags}", cwd=self.source_folder)
            self.run(f"{ar} rcs containers.a *.o", cwd=self.source_folder)
            self.run("rm -f *.o", cwd=self.source_folder)

    def package(self):
        copy(self, "src/include/*.h", self.source_folder,
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "containers.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "src/include/VERSION", self.source_folder,
             os.path.join(self.package_folder, "include"), keep_path=False)
        # Upstream Makefile names the archive `containers.a` (no lib prefix);
        # CMake find_library expects `libcontainers.a`/`libcontainers.so`, so
        # rename on install into the package lib dir.
        if os.path.exists(os.path.join(self.source_folder, "containers.a")):
            copy(self, "containers.a", self.source_folder,
                 os.path.join(self.package_folder, "lib"), keep_path=False)
            os.rename(os.path.join(self.package_folder, "lib", "containers.a"),
                      os.path.join(self.package_folder, "lib", "libcontainers.a"))
        if os.path.exists(os.path.join(self.source_folder, "containers.so")):
            copy(self, "containers.so", self.source_folder,
                 os.path.join(self.package_folder, "lib"), keep_path=False)
            os.rename(os.path.join(self.package_folder, "lib", "containers.so"),
                      os.path.join(self.package_folder, "lib", "libcontainers.so"))

    def package_info(self):
        self.cpp_info.libs = ["containers"]
        # README documents linking with -ldl; library itself needs no dl
        # symbols, so system_libs stays empty unless consumer requires it.
