#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/bitcoin/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class BitcoinTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # 消费者编译/链接验证:编译包含包头的 test.cpp 并链接 bitcoin::bitcoin,
        # 校验 package() 复制的头文件与静态库可被下游消费。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: test_bitcoin 与消费者程序均动态依赖 libevent/libc++_shared,
        # 手动注入 LD_LIBRARY_PATH(依赖配方未声明 runenv_info)。
        env = Environment()
        for dep in ("libevent", "sqlite3", "boost"):
            lib_dir = os.path.join(self.dependencies[dep].package_folder, "lib")
            if os.path.isdir(lib_dir):
                env.append_path("LD_LIBRARY_PATH", lib_dir)
        libcxx_dir = os.path.join(self.dependencies["bitcoin"].package_folder, "lib")
        if os.path.isdir(libcxx_dir):
            env.append_path("LD_LIBRARY_PATH", libcxx_dir)
        # 沙箱 uid 映射会导致临时目录权限检查失败。
        # 实测(2026-08-18): TMPDIR 指向 CI 同款路径 /data/storage/el2/base/cache
        # (可写且属主正确)后,上游 734 用例全量实跑 *** No errors detected;
        # 用户主目录亦可用, build_folder 下目录会权限失败。
        tmpdir = "/data/storage/el2/base/cache"
        if not os.path.isdir(tmpdir) or not os.access(tmpdir, os.W_OK):
            tmpdir = os.path.expanduser("~")
        env.define("TMPDIR", tmpdir)
        testdatadir = os.path.join(tmpdir, "btc-testdatadir")
        os.makedirs(testdatadir, exist_ok=True)
        os.chmod(testdatadir, 0o777)

        # 1) 运行消费者程序(验证头文件与静态库链接正确)
        consumer_bin = os.path.join(self.cpp.build.bindirs[0], "test_bitcoin")
        self.output.info(f"Running consumer {consumer_bin}")
        with env.vars(self).apply():
            self.run(consumer_bin, env="conanrun")

        # 2) 运行主包安装的 test_bitcoin 全量 734 用例(与 MANIFEST.yml 声明的上游测试一致)。
        package_folder = self.dependencies["bitcoin"].package_folder
        # bitcoin >=31 的 CMake 将内部二进制安装到 libexec/,部分构建在 bin/,取存在的路径
        test_bin = None
        for rel in ("libexec", "bin"):
            cand = os.path.join(package_folder, rel, "test_bitcoin")
            if os.path.isfile(cand):
                test_bin = cand
                break
        if test_bin is None:
            raise RuntimeError(f"test_bitcoin not found under {package_folder}/{{libexec,bin}}")
        self.output.info(f"Running {test_bin} (full 734 upstream cases, TMPDIR={tmpdir})")
        with env.vars(self).apply():
            self.run(f"{test_bin} -- -testdatadir={testdatadir}", env="conanrun")
