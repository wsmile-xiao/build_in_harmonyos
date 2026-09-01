#!/usr/bin/env python3
"""Conan recipe — luajit-openresty 2.1-20260311.1 (custom Makefile).

LuaJIT (OpenResty fork) uses a custom Makefile (not autotools/cmake).
Build produces a static library (libluajit-5.1.a) and a statically
linked luajit executable.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuajitOpenrestyConan(ConanFile):
    name = "luajit-openresty"
    version = "2.1-20260311.1"
    description = "OpenResty's Branch of LuaJIT 2 - High-performance Lua interpreter with JIT compiler"
    license = "MIT"
    homepage = "https://github.com/openresty/luajit2"
    url = "https://github.com/openresty/luajit2"

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
        # R33: Get compiler from Conan conf, never from shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # Derive ar from compiler path (e.g. /data/service/hnp/bin/clang → /data/service/hnp/bin/ar)
        cc_dir = os.path.dirname(cc)
        ar = os.path.join(cc_dir, "ar")
        if not os.path.exists(ar):
            ar = os.path.join(cc_dir, "llvm-ar")
        # OHOS /tmp is read-only; tell clang and make to use build folder for temp files
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env_vars = f'TMPDIR="{tmpdir}"'
        # LuaJIT Makefile variables:
        #   CC        — host compiler (for minilua, buildvm)
        #   TARGET_CC — target compiler (for library objects)
        #   TARGET_AR — archiver (TARGET_AR= $(CROSS)ar rcus)
        # Pass CROSS="" to disable cross prefix, CC for host, TARGET_CC for target.
        # BUILDMODE=static: static library + statically linked luajit executable.
        # R9: Always use -j1
        # R8: Pass mremap-disable flag via CFLAGS (not via platform macro in patch)
        extra_cflags = ""
        if self.settings.os == "OHOS":
            extra_cflags = "TARGET_CFLAGS=-DLJ_ALLOC_NO_MREMAP"
        self.run(
            f'{env_vars} make CROSS="" CC="{cc}" TARGET_CC="{cc}" '
            f'TARGET_AR="{ar} rcus" {extra_cflags} BUILDMODE=static -j1',
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        # Copy artifacts directly from source build tree — avoid make install
        # because OHOS forbids symlinks in staging directories.
        # Static library: source produces libluajit.a, rename to libluajit-5.1.a
        # to match the standard pkg-config / LuaJIT convention.
        copy(self, "libluajit.a", os.path.join(src, "src"),
             os.path.join(pkg, "lib"))
        os.rename(
            os.path.join(pkg, "lib", "libluajit.a"),
            os.path.join(pkg, "lib", "libluajit-5.1.a"),
        )
        # Headers
        for h in ["lua.h", "lualib.h", "lauxlib.h", "luaconf.h", "lua.hpp", "luajit.h"]:
            copy(self, h, os.path.join(src, "src"),
                 os.path.join(pkg, "include", "luajit-2.1"))
        # Executable (find the versioned name: luajit-2.1.XXXXXXXXXX)
        copy(self, "luajit*", os.path.join(src, "src"),
             os.path.join(pkg, "bin"))
        # JIT lua runtime files
        copy(self, "*.lua", os.path.join(src, "src", "jit"),
             os.path.join(pkg, "share", "luajit-2.1", "jit"))

    def package_info(self):
        self.cpp_info.libs = ["luajit-5.1"]
        self.cpp_info.includedirs = ["include/luajit-2.1"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "luajit-openresty")
        self.cpp_info.set_property("cmake_target_name", "luajit-openresty::luajit-openresty")
