#!/usr/bin/env python3
"""Conan recipe — lz4 1.10.0.3 (fast compression library + CLI tool).

R37 版本后缀（与 1.10.0 同上游源码 v1.10.0，修复适配问题）：
main 已并行合入 1.10.0.1 与 1.10.0.2（后者仅静态构建，BUILD_SHARED=no），
本版取 R37 下一序号 1.10.0.3，不覆盖任何已合入内容：
- 修复 shared 构建：v1.10.0 顶层 Makefile 没有 `lib-shared` 目标
  （1.10.0 与 main 现有 1.10.0.1 配方在 shared=True 时均会报
  No rule to make target），改为 `make -C lib lib`（lib/Makefile 的
  lib 目标同时产出 liblz4.a 与带版本号的 liblz4.so*）。
- 吸收 1.9.4 配方验证过的 OHOS 环境加固：E132（lld 依赖
  libxml2.so.16）、受限 /bin/sh、hmdfs 拒绝 symlink；其中 make 的
  SHELL 覆盖改为按存在性自适应——/data/service/hnp/bin/bash 仅
  CI worker 存在，真机无此路径但 /bin/sh 可用（1.10.0 同源实证）。
- 修正 test_package/MANIFEST.yml 上游测试引用（check_mex.c 在
  v1.10.0 源码中不存在，改为实际存在的测试目标）。

Build system: pure Makefile (no configure script).
R38: includes lz4 CLI tool → commands.json required.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Lz4Conan(ConanFile):
    name = "lz4"
    version = "1.10.0.3"
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
        # OHOS SDK 的 lld 链接器依赖 libxml2.so.16（E132）。CI profile 已带
        # LD_LIBRARY_PATH，但历史上曾被误删过——配方级再注入一次兜底
        #（同 lz4 1.9.4 配方做法）。路径不存在时跳过（host 构建不受影响）。
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(llvm_lib):
            os.environ["LD_LIBRARY_PATH"] = llvm_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

        # POSIX_ENV=Yes: HarmonyOS uname -s returns 'HarmonyOS' which is not in
        # the default POSIX_ENV check list; pass explicitly for safety.
        # SHELL: CI worker 的受限 /bin/sh 需要 /data/service/hnp/bin/bash，
        # 但真机（10.62.134.118）无该路径且其 /bin/sh 可用（1.10.0 同源
        # 已实证）→ 按存在性自适应，两环境各有实证运行背书。
        # No CC default in lz4 Makefiles → pass clang explicitly (toolchain).
        # LN_SF=cp: OHOS user home is on hmdfs which rejects symlinks; the
        # versioned shared-lib links (ln -sf) would fail, so use cp instead.
        # Top-level default target = lib-release + lz4-release → liblz4.a + CLI.
        make_vars = "POSIX_ENV=Yes CC=clang CXX=clang++ LN_SF=cp"
        ci_bash = "/data/service/hnp/bin/bash"
        if os.path.exists(ci_bash):
            make_vars += " SHELL=" + ci_bash
        make_cmd = "make -j1 " + make_vars
        self.run(make_cmd, cwd=self.source_folder)
        if self.options.shared:
            # v1.10.0 顶层无 lib-shared 目标，进入 lib/ 构建共享库
            self.run(make_cmd + " lib", cwd=self.source_folder + "/lib")

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
