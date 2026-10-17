#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/s/soci/4.0.3/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SociTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv 生成 conanrun 环境（LD_LIBRARY_PATH 覆盖 libsoci* 与依赖 lib）——
    # 缺它时 cmake.test() 起的 test_soci 在动态加载期即报
    # "Error loading shared library libsoci_sqlite3.so.4.0"（2026-09-23 首验实证）。
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # soci-sqlite3.h 直接 #include <sqlite3.h>，而本版 conan 的 CMakeDeps 没为
        # 「透传依赖」在测试侧落盘 sqlite3-config.cmake（2026-09-23 实证：generators/
        # 里只有 soci-* 文件、soci data.cmake 的 find_dependency 名单为空 append）
        # ⇒ 显式直连同版本（与 soci 传递要求同版，图内自动去重）拿到 include+target。
        self.requires("sqlite3/3.53.4")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 双保险（矩阵二分实证 2026-09-23）：
        # (1) 内联 LD_LIBRARY_PATH（presage 草稿方：内联变量优先于 env 注入）＝全部
        #     依赖 libdir + 主包 build 树 lib（LD 指 build 树在本机矩阵中 100% 可载）
        #     + SDK llvm lib（libc++_shared，VirtualRunEnv 挂不到）；
        # (2) 保留 env="conanrun"（cbqn/0.12.0 先例）兜底。
        # ctest 直跑替代 cmake.test()（其 env 默认空串，传参链路在本机实测不可靠）。
        # conan 缓存布局：…/<pkgid>/{p,b} —— p 与 b 是 sociHASH 的同级兄弟，
        # 故从 …/pkgid/p 出发**一级 pardir** 回到 pkgid 再进 b（多走一级会得到
        # …/p/b/b/… 恒不存在——W4 审计实证修正，旧路径致该双保险从未生效）。
        soc = self.dependencies["soci"].package_folder
        bd_lib = os.path.normpath(os.path.join(soc, os.pardir,
                                               "b", "build", "Release", "lib"))
        sdk = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        # ⚠ 顺序敏感（矩阵实锤）：LD 首个命中者定生死——build 树字节已证 100% 可载，
        # 必须排最前；SDK llvm 提供 libc++_shared（VirtualRunEnv 挂不到）。
        order = []
        if os.path.isdir(bd_lib):
            order.append(bd_lib)
        if os.path.isdir(sdk):
            order.append(sdk)
        for _ref, dep in self.dependencies.items():
            order.append(os.path.join(dep.package_folder, "lib"))
            for _d in dep.cpp_info.libdirs:
                if os.path.isabs(_d):
                    order.append(_d)
                else:
                    order.append(os.path.join(dep.package_folder, _d))
        ld = os.pathsep.join(dict.fromkeys(d for d in order if d))
        self.run(f'LD_LIBRARY_PATH="{ld}" ctest --test-dir "{self.build_folder}" '
                 f'--output-on-failure', env="conanrun")
