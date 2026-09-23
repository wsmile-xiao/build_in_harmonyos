#!/usr/bin/env python3
# test_package/conanfile.py — libotf/0.9.16 消费者测试与鸿蒙平台校验（R34/R40）
#
# 用例清单（详见本目录 MANIFEST.yml）：
#   单元测试 1 例  test.sh → ./test_consumer：消费者视角链接安装后的 libotf，
#                  调用 OTF_* 公开 API 并经 freetype 逐字符交叉验证 cmap
#   集成测试 4 例  test.sh → otfdump / otflist / otftobdf 三个上游程序端到端
#                  + 损坏字体负向用例
#   鸿蒙特有 1 例  test_ohos.sh → 安装产物 ELF64/AArch64、SONAME、NEEDED(freetype)、
#                  .codesign、公开头文件与 pkg-config 契约

import os
import shutil

from conan import ConanFile


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dep_dirs(self):
        """被测包自身 lib 目录 + 全部依赖（含传递依赖）的 include/lib 目录。"""
        incs, libdirs = [], []
        pkg = self.dependencies[self.tested_reference_str].package_folder
        for _ref, dep in self.dependencies.items():
            for p in dep.cpp_info.includedirs:
                q = p if os.path.isabs(p) else os.path.join(dep.package_folder, p)
                if os.path.isdir(q) and q not in incs:
                    incs.append(q)
            for p in dep.cpp_info.libdirs:
                q = p if os.path.isabs(p) else os.path.join(dep.package_folder, p)
                if os.path.isdir(q) and q not in libdirs:
                    libdirs.append(q)
        return pkg, incs, libdirs

    def _ld_library_path(self, pkg, libdirs):
        """本机即目标机（OHOS PC 上原生构建并运行）。OHOS 运行时无系统 freetype
        （E505），需手动把包内及全部依赖（含传递依赖）的 lib 目录加入
        LD_LIBRARY_PATH，工具与消费者才能解析 SONAME 依赖。"""
        paths = [os.path.join(pkg, "lib")] + list(libdirs)
        existing = os.environ.get("LD_LIBRARY_PATH")
        if existing:
            paths.append(existing)
        return ":".join(paths)

    def build(self):
        # 消费者编译：只使用包内头文件/库。otf.h 内部包含 <ft2build.h>/
        # FT_FREETYPE_H，故 freetype（传递依赖）的 include 必须一并提供——
        # 这正是 recipe 声明 transitive_headers/transitive_libs 的原因。
        cc = os.environ.get("CC", "clang")
        _pkg, incs, libdirs = self._dep_dirs()
        inc = " ".join("-I" + p for p in incs)
        lib = " ".join("-L" + p for p in libdirs)
        self.run(f"{cc} test.c -o test_consumer {inc} {lib} -lotf -lfreetype")

    def test(self):
        pkg, _incs, libdirs = self._dep_dirs()
        ld_path = self._ld_library_path(pkg, libdirs)
        # 平台脚本统一用 bash 执行（系统 /system/bin/sh 为 mksh，语义差异较多）：
        # bash 定位按 CONFIG_SHELL → PATH 中 bash → sh 依次回退。
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "sh"
        # 单元测试 1 例 + 集成测试 4 例
        self.run(f"LD_LIBRARY_PATH='{ld_path}' {bash} ./test.sh '{pkg}' ./test_consumer",
                 env="conanrun")
        # 鸿蒙特有测试 1 例（独立统计）
        self.run(f"LD_LIBRARY_PATH='{ld_path}' {bash} ./test_ohos.sh '{pkg}' ./test_consumer",
                 env="conanrun")
        self.output.info("libotf: 单元 1 + 集成 4 + 鸿蒙特有 1 用例全部通过")
