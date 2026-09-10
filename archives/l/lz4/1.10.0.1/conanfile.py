#!/usr/bin/env python3
"""Conan recipe — lz4 1.10.0.1 (fast compression library + CLI tool).

Build system: pure Makefile (no configure script).
R38: includes lz4 CLI tool → commands.json required.

1.10.0.1 (R37 适配修复升版): lz4/1.10.0 已在制品仓发布、recipe 固化，无法在同一
版本上修改 conanfile.py；因此以 .1 版本后缀承载纯 Makefile 的编译器注入修复
（OHOS 工具链无 `cc`，须把 Conan conf 里的 clang 以 CC/CXX/AR/RANLIB 传给 make，
与 bzip2/zlib 同模式）。源码仍是上游 lz4 v1.10.0。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Lz4Conan(ConanFile):
    name = "lz4"
    version = "1.10.0.1"
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
        # lz4 uses a pure Makefile.  The default CC is `cc`, which is absent
        # from the OHOS toolchain, so read the compiler out of the Conan conf
        # (same pattern as the bzip2/zlib recipes) and pass it to make.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        make_env = (f"CC={cc} CXX={cxx} AR=llvm-ar RANLIB=llvm-ranlib "
                    "POSIX_ENV=Yes")
        # POSIX_ENV=Yes is kept explicit: upstream auto-detect only matches
        # known POSIX unames, not the OHOS/HarmonyOS kernel.
        # Run in source_folder — lz4 Makefile is in the root source dir.
        self.run(f"make -j1 {make_env}", cwd=self.source_folder)
        if self.options.shared:
            self.run(f"make -j1 {make_env} lib-shared", cwd=self.source_folder)

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
