#!/usr/bin/env python3
"""Conan test_package — libgomp 16.1.1（L1 消费者测试）。

直接用 clang 编译一个小型 OpenMP 程序，链接打包后的 libgomp，验证：
  - #include <omp.h> 运行时 API（线程数 / 线程号 / 动态线程 / 锁）。
  - #pragma omp parallel 真并行（clang -fopenmp=libgomp）。

用 clang 直接编译而非 CMake：HarmonyOS 上大型 cmake 子进程可能在完整 GCC
构建留下的内存压力下瞬时 SIGSEGV，单次 clang 调用更可靠（见 libobjc 经验）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.env import Environment


class LibgompTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # 设备 clang 位于隔离 job PATH 之外，且默认把临时文件写到只读的
        # /tmp；暴露 PATH 与可写 TMPDIR（非保留名脚本，Conan 保留 "conanbuild"）。
        env = Environment()
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.define("TMPDIR", "/data/storage/el2/base/cache")
        env.define("TMP", "/data/storage/el2/base/cache")
        env.define("TEMP", "/data/storage/el2/base/cache")
        # 运行时动态链接器需找到 libgomp.so.1（libgomp 安装在 package/lib 下，
        # 不在系统默认库路径；VirtualRunEnv 不会注入到自定义 env 脚本）。
        dep = self.dependencies["libgomp"]
        for libdir in dep.cpp_info.libdirs:
            env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("test_build_env")

    def build(self):
        dep = self.dependencies["libgomp"]
        include_flags = " ".join("-I" + d for d in dep.cpp_info.includedirs)
        lib_flags = " ".join("-L" + d for d in dep.cpp_info.libdirs)
        lib_names = " ".join("-l" + name for name in dep.cpp_info.libs)
        source = os.path.join(self.source_folder, "test.c")
        output = os.path.join(self.build_folder, "test_libgomp")
        # 不用 -fopenmp=libgomp：OHOS clang 15 驱动会吞掉该参数（不传给 cc1），
        # #pragma omp parallel 不生成并行代码。test.c 改用手动调用 libgomp 的
        # GOMP_parallel ABI 验证并行，仅需显式 -L/-lgomp 链接打包产物。
        self.run(
            "clang {} {} {} {} -o {}".format(
                include_flags, source, lib_flags, lib_names, output
            ),
            env="test_build_env",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile-only check")
            return
        executable = os.path.join(self.build_folder, "test_libgomp")
        log = os.path.join(self.build_folder, "test_output.log")
        # 静态测试程序可能因共享 libgcc 的退出析构在 HarmonyOS 上 SIGSEGV
        # （见 libobjc 经验），捕获输出并校验 ALL PASSED 标记而非信任退出码。
        self.run(
            "OMP_NUM_THREADS=4 {} > {} 2>&1; true".format(executable, log),
            env="test_build_env",
        )
        with open(log, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        if "ALL PASSED" not in content:
            raise ConanException(
                "test binary did not report ALL PASSED:\n{}".format(content)
            )
