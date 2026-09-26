#!/usr/bin/env python3
"""Conan recipe — sexpp-cli 0.9.2（CMake，CLI application）

交付物：上游 `sexpp` 命令行工具（bin/sexpp），application 型单二进制包。

归属划分（判据详 notes.md）：库制品（libsexpp / include / sexpp.pc）归父包
archives/s/sexpp（在档 0.8.7、0.9.1）；父包 0.9.2 不在制品仓 ⇒ 本包**不
requires 父包**，按 v0.9.2 源码整编（BUILD_SHARED_LIBS=OFF 静态内嵌
libsexpp），package() 只交 CLI 二进制，包内不出现 lib/、include/。

上游 GoogleTest 套件（tests/src/*.cpp，源码宏清点 82）在 build() 内经
ctest 真跑：
- DOWNLOAD_GTEST=OFF：上游 FetchContent 从 github.com 拉 googletest，
  真机不可达；googletest 改由 test_requires gtest/1.17.0（制品仓）提供；
- 接线关键：CMakeDeps 只导出 gtest::gtest 命名，而上游 DOWNLOAD_GTEST
  的 else 分支写死 FindGTest 模块式目标 GTest::Main / GTest::GTest ⇒ 必须
  把 GTest_DIR 指向 gtest 包内 lib/cmake/GTest 的上游 GTestConfig.cmake
  （W0 探针 find_package(GTest)+GTest::Main/GTest::GTest configure+build
  rc=0 实证；父包 0.8.7 同法）；
- gtest/1.17.0 自带 0001-tmpdir-ohos-sandbox.patch：CaptureStdout scratch
  只认 TMPDIR ⇒ build() 跑 ctest 前导出 TMPDIR=<build>/gtest-tmp（可写
  目录），父包卡死的 2 个捕获流用例在本包复活（W0 preview 70/70 实证）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class SexppCliConan(ConanFile):
    name = "sexpp-cli"
    version = "0.9.2"
    description = "sexpp S-expression command-line tool (CLI of the sexpp library)"
    license = "MIT"
    homepage = "https://github.com/rnpgp/sexpp"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # 上游单元测试需要 googletest；test_requires 只进 build()，不进消费方闭包。
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CLI 静态整编：libsexpp 编进二进制，包内不产库制品（归属见 notes.md）
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["WITH_SEXP_CLI"] = "ON"
        # 上游测试真的跑（build() 内 ctest，82 用例）
        tc.variables["WITH_SEXP_TESTS"] = "ON"
        # 真机不可达 github.com：禁止 FetchContent 拉 googletest
        tc.variables["DOWNLOAD_GTEST"] = "OFF"
        # CMakeDeps 只给 gtest::gtest，上游 else 分支要 GTest::Main/GTest::GTest：
        # 钉死到 gtest 包内上游 GTestConfig.cmake（find_package(GTest) config 模式
        # 优先读 <pkg>_DIR cache 变量，确定性命中）
        gtest = self.dependencies.get("gtest")
        if gtest:
            tc.variables["GTest_DIR"] = os.path.join(
                gtest.package_folder, "lib", "cmake", "GTest").replace("\\", "/")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 配方自限时（E618 模式）：conan 自带 -j<cpu_count>（本机 20 vs affinity 8）
        # 被后附的 build_tool_args 覆盖，GNU make 对重复 -j 取最后一个
        jobs = self.conf.get("tools.build:jobs", default=None, check_type=int) or 1
        cmake.build(build_tool_args=[f"-j{jobs}"])
        if can_run(self):
            # gtest 捕获流 scratch 只认 TMPDIR（OHOS /tmp 只读）；指向可写构建目录
            tmpdir = os.path.join(self.build_folder, "gtest-tmp")
            os.makedirs(tmpdir, exist_ok=True)
            test_env = Environment()
            test_env.define("TMPDIR", tmpdir)
            test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
            with test_env.vars(self).apply():
                cmake.test()

    def package(self):
        # 归属划分：只交 CLI；cmake.install() 会带出 lib/include/pc/man（归父包面）
        bin_dir = os.path.join(self.build_folder, "bin")
        cli = os.path.join(bin_dir, "sexpp")
        if not os.path.isfile(cli):
            raise ConanException(f"sexpp CLI binary not found: {cli}")
        copy(self, "sexpp", src=bin_dir,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        # CLI 应用：只有 bin/；清空默认 include/lib 路径避免空目录告警
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
