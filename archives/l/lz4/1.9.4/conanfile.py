#!/usr/bin/env python3
"""Conan recipe — lz4 1.9.4 (fast compression library + CLI tool).

Build system: pure Makefile (no configure script).
R38: includes lz4 CLI tool → commands.json required.

NOTE (1.9.4 vs 1.10.0): upstream top-level `make` (default target) builds
`lib-release` + `lz4-release` → liblz4.a + `lz4` CLI. There is no
`lib-shared` top-level target in 1.9.4 (unlike 1.10.0); shared library is
built via `make -C lib` (lib/Makefile `lib: liblz4.a liblz4`).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Lz4Conan(ConanFile):
    name = "lz4"
    version = "1.9.4"
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
        # OHOS SDK 的 lld 链接器依赖 libxml2.so.16（E132）。CI 环境未带
        # LD_LIBRARY_PATH，导致链接动态库/可执行时 lld 加载失败
        # （"Error loading shared library libxml2.so.16: ... needed by .../lld"）。
        # 构建前显式把 SDK 的 llvm/lib 加入 LD_LIBRARY_PATH。
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        os.environ["LD_LIBRARY_PATH"] = llvm_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

        # POSIX_ENV=Yes: HarmonyOS uname -s returns 'HarmonyOS' which is not in
        # the default POSIX_ENV check list; pass explicitly for safety.
        # OHOS /bin/sh is restricted → pass an available bash as make SHELL.
        # No CC default in lz4 Makefiles → pass clang explicitly (toolchain).
        # LN_SF=cp: OHOS user home is on hmdfs which rejects symlinks; the
        # shared-lib versioned links (ln -sf) would fail, so use cp instead.
        # Top-level `make` builds liblz4.a (lib-release) + `lz4` CLI (lz4-release).
        make_cmd = ("make -j1 POSIX_ENV=Yes SHELL=/data/service/hnp/bin/bash "
                    "CC=clang CXX=clang++ LN_SF=cp")
        self.run(make_cmd, cwd=self.source_folder)
        if self.options.shared:
            # 1.9.4 has no top-level lib-shared; build shared in lib/ dir
            self.run(make_cmd, cwd=self.source_folder + "/lib")

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
