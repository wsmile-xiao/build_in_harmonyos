#!/usr/bin/env python3
"""nanodbc 2.14.0 test_package —— 真实消费者（C++，只用交付的包）。

① 消费者离线冒烟（9 项断言）：connection/statement/result 默认构造语义、
   未连接 disconnect()/reset() no-op、transactions()==0、date/time/timestamp
   POD、database_error 离线构造——全部不依赖数据库服务（OHOS PC 沙箱无
   ODBC 数据源），但每一处调用都真实经过交付库符号。
② 上游官方测试（utility_test 的 TEST_CASE "convert"，纯离线）在源码树独立
   构建中真跑（ctest -R utility_tests）；DB 型测试需 TEST_NANODBC_CONNSTR
   真数据库连接，沙箱环境排除，如实记录于 notes.md 与 PR 统计表。

本测试真依赖被测包：CI 的 L1e 会把 lib/、include/ 移走后重跑 conan test，
届时 find_package(nanodbc) 必定失败。
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class NanodbcTestConan(ConanFile):
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

    def _ohos_runtime_libdirs(self):
        # OHOS 沙箱：conanrun 环境不含 SDK/system 库路径，
        # 动态加载器找不到 libc++_shared.so/libxml2 等——
        # 按仓库惯例（acsccid/abseil 同款）命令内联 LD_LIBRARY_PATH。
        dirs = []
        dep = self.dependencies["unixodbc"]
        dirs.extend(dep.cpp_info.libdirs)
        if str(self.settings.os) == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            cxx = compilers.get("cpp") or compilers.get("c")
            if cxx:
                compiler = os.path.realpath(cxx)
                llvm_dir = os.path.dirname(os.path.dirname(compiler))
                # lld 依赖 libxml2.so.16（链接期符号依赖）
                dirs.append(os.path.join(llvm_dir, "lib"))
                # libc++_shared.so / libunwind 等 target 侧库
                dirs.append(os.path.join(llvm_dir, "lib", "aarch64-linux-ohos"))
                # 系统真 libc++_shared.so（真身在系统分区，SDK 内同名文件是链接器脚本）
                dirs.append("/system/lib64")
        return [d for d in dict.fromkeys(dirs) if d]

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：defer execution to a HarmonyOS PC device")
            return
        env = "LD_LIBRARY_PATH=%s" % ":".join(self._ohos_runtime_libdirs())
        self.run('%s "'
                 '%s"' % (env, os.path.join(self.cpp.build.bindir, "test_nanodbc")))
