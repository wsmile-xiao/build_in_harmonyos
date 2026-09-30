#!/usr/bin/env python3
"""libsoci 4.0.3 test_package —— 真实 C++ 消费者。

① **完整消费者用例（平台 rule12）**：`test_libsoci.cpp` 用 SQLite3 后端把 SOCI
   当成真实消费者跑一整条数据访问链路（预编译语句 + use 绑定 + rowset/row 迭代 +
   列元数据 + NULL 指示器 + 事务提交/回滚 + 参数化查询 + 错误处理 +
   sqlite_api 版本/系统表），共 15 项可核对结果。
② 上游官方测试（catch + CTest）在 recipe 的 build() 里跑（CI 为原生 OHOS 构建）。

test_package 的链接与编译**真正依赖被测包**：CI 的 L1e（R34）会把 lib/、include/
移走后重跑 conan test，本测试必须因此编译失败（真测试）。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LibsociTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译 + 链接（原生构建时才会执行）")
        else:
            binary = os.path.join(self.cpp.build.bindirs[0], "test_libsoci")
            self.run(binary, env="conanrun")
        # ② 适配自检（M，非上游用例）：交付形态（库/头/许可/CMake 集成/纯净性）
        import sys as _sys
        layout = os.path.join(self.source_folder, "test_layout.py")
        # 必须把被测包的 package_folder 传给自检脚本（它也支持直接读 argv[1]）
        self.run("%s %s %s" % (_sys.executable, layout,
                               self.dependencies["libsoci"].package_folder))
