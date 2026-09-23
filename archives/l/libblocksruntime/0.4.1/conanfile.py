#!/usr/bin/env python3
"""Conan recipe for BlocksRuntime 0.4.1 — the runtime library that backs the
clang `-fblocks` language extension (the BlocksRuntime portion of LLVM's
compiler-rt, packaged by distributions as `libblocksruntime`).

Why this package exists: on OHOS the clang toolchain implements `-fblocks`
(blocks compile fine) but ships **no** Blocks runtime, so any consumer ends up
with undefined `_Block_copy` / `_Block_release` / `_Block_object_assign` /
`_Block_object_dispose` / `_NSConcrete*Block` symbols at link time. This recipe
builds the upstream 0.4.1 sources (runtime.c + data.c) into `libBlocksRuntime.a`
and installs `Block.h` / `Block_private.h`, so that `-fblocks` code links.

Version note: upstream mackyle/blocksruntime publishes no `0.4.1` tag; `0.4.1`
is the release identity of the distribution source archive
(`libblocksruntime_0.4.1.orig.tar.gz`, AC_INIT([libBlocksRuntime], [0.4.1])),
which carries the autotools packaging plus the release `runtime.c` / `data.c`.

The upstream autotools build was intentionally not used: its 2013
`config.guess`/`config.sub` do not recognise HarmonyOS (E007) and `make`
on HMDFS hits the jobserver FIFO restriction (E074). The build is exactly two
translation units, so it is compiled directly, which is deterministic here.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class LibBlocksRuntimeConan(ConanFile):
    name = "libblocksruntime"
    version = "0.4.1"
    description = "BlocksRuntime: runtime library for clang -fblocks (compiler-rt BlocksRuntime)"
    license = "MIT OR UIUC"
    homepage = "https://github.com/mackyle/blocksruntime"
    url = "https://github.com/mackyle/blocksruntime"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "LICENSE.TXT", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        self._cc = str(executables.get("c") or "clang")
        ar = executables.get("ar") or ""
        if not ar:
            bindir = os.path.dirname(str(executables.get("c") or "").strip())
            if bindir:
                for cand in ("llvm-ar", "ar"):
                    full = os.path.join(bindir, cand)
                    if os.path.isfile(full):
                        ar = full
                        break
        self._ar = str(ar or "ar")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        build = self.build_folder
        opt = "-O2" if self.settings.build_type == "Release" else "-g -O0"

        save(self, os.path.join(build, "config.h"),
             '#define PACKAGE_VERSION "0.4.1"\n')

        objects = []
        for name in ("runtime", "data"):
            obj = os.path.join(build, name + ".o")
            objects.append(obj)
            self.run(
                f'{self._cc} -c {opt} -std=c99 -fPIC '
                f'-I "{src}" -I "{build}" -o "{obj}" "{src}/{name}.c"'
            )
        self.run(f'{self._ar} rcs "{build}/libBlocksRuntime.a" '
                 + " ".join(f'"{obj}"' for obj in objects))

    def package(self):
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libBlocksRuntime.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE.TXT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["BlocksRuntime"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # Linking this runtime is only ever needed by code compiled with
        # -fblocks; propagate the language flag so consumers do not have to
        # know about the split between the compiler feature and the runtime.
        self.cpp_info.cflags = ["-fblocks"]
        self.cpp_info.cxxflags = ["-fblocks"]
        self.cpp_info.set_property("cmake_file_name", "BlocksRuntime")
        self.cpp_info.set_property("cmake_target_name", "BlocksRuntime::BlocksRuntime")
