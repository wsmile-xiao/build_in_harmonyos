#!/usr/bin/env python3
"""Conan recipe — rcheevos 12.2.1 (C, static library, no upstream build system).

RetroAchievements toolkit: achievement trigger/lboard/rich-presence runtime,
API request/response helpers and ROM/disc/zip hash generation. Pure C89,
zero third-party dependencies (bundled MD5/AES), public headers in include/.

Upstream ships no build system for the library itself — consumers compile
src/**.c directly. This recipe:
  1. builds and RUNS the full upstream test suite (test/Makefile, thousands
     of assertions, R51) — also compiles the library objects as a side effect;
  2. archives the src/**.o objects into lib/librcheevos.a.
Upstream test/Makefile only knows ARCH=x86/x64 (-m32/-m64); on aarch64 we
pass ARCH=x64 — clang accepts -m64 there (verified on device).

Reference: archives/f/fp16/cci.20210320 (no-layout), archives/z/zsync/0.6.3
(direct-compile family).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class RcheevosConan(ConanFile):
    name = "rcheevos"
    version = "12.2.1"
    description = "RetroAchievements toolkit: achievement runtime, rapi helpers and ROM/disc/zip hashing (C89, no deps)"
    license = "MIT"
    homepage = "https://github.com/RetroAchievements/rcheevos"
    url = "https://github.com/RetroAchievements/rcheevos"
    topics = ("achievements", "retroarch", "emulation", "hashing", "c89")

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass  # single-tree layout (build == source): patches and make share one tree

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Upstream test suite builds library objects into src/ as a side
        # effect, then runs the whole framework (R51: real upstream tests in
        # conan create log, CI L1c evidence).
        cc = (self.conf.get("tools.build:compiler_executables") or {}).get("c", "clang")
        test_dir = os.path.join(self.source_folder, "test")
        self.run(f"make -C {test_dir} ARCH=x64 CC={cc} runtests", env="conanbuild")

        # Archive the library objects (src/**.o; test/**.o are excluded by path).
        objs = sorted(glob.glob(os.path.join(self.source_folder, "src", "**", "*.o"), recursive=True))
        if not objs:
            raise ConanException("no library objects produced by upstream make")
        libdir = os.path.join(self.build_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        lib = os.path.join(libdir, "librcheevos.a")
        obj_list = " ".join(objs)
        # ar vs llvm-ar: whichever the build environment exposes on PATH.
        self.run(f"(ar rcs {lib} {obj_list}) 2>/dev/null || llvm-ar rcs {lib} {obj_list}", env="conanbuild")

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "librcheevos.a", src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["rcheevos"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "rcheevos")
        self.cpp_info.set_property("cmake_target_name", "rcheevos::rcheevos")
        # Public headers are plain C89; consumers of any language may link.
        self.cpp_info.set_property("pkg_config_name", "rcheevos")
