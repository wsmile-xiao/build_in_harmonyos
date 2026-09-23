#!/usr/bin/env python3
"""test_package for libint2 — 消费者视角验证（Conan L1）。

四个独立消费者入口（唯一入口计数，不按内部断言重复计）：
  1. test_package     C++ API（BasisSet + Engine）：重叠矩阵 / 库仑积分
  2. test_c_api       C ABI：内核分发表 / 内存需求查询 / init-cleanup 生命周期
  3. test_basis       基组数据库：按名加载 + 未知基组名必须报错
  4. test_pkgconfig   pkg-config 消费契约：用安装出来的 libint2.pc 编译并运行
"""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        for entry in ("test_package", "test_c_api", "test_basis"):
            self.run(os.path.join(bindir, entry), env="conanrun")
        self._test_pkgconfig_consumer()

    def _test_pkgconfig_consumer(self):
        """用安装出来的 libint2.pc 编译并运行 test_pkgconfig.c。

        上游 libint2.pc.in 是 autotools 模板，经 CMake 渲染后前缀/版本为空；
        本配方在 package() 中重写该文件，这里是对该修复的回归守卫。
        """
        pkg_config = shutil.which("pkg-config")
        if not pkg_config:
            raise ConanException("pkg-config 不在 PATH 中，无法验证 .pc 消费契约")
        pc_dir = os.path.join(self.dependencies["libint2"].package_folder,
                              "lib", "pkgconfig")
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = os.pathsep.join(
            [pc_dir, env.get("PKG_CONFIG_PATH", "")]).rstrip(os.pathsep)

        def pkg_config_flags(option):
            out = subprocess.run([pkg_config, option, "libint2"], env=env,
                                 capture_output=True, text=True)
            if out.returncode != 0:
                raise ConanException(
                    f"pkg-config {option} libint2 失败: {out.stderr.strip()}")
            return out.stdout.split()

        cflags = pkg_config_flags("--cflags")
        libs = pkg_config_flags("--libs")
        # R33：编译器取自 profile，不用 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or compilers.get("cpp") or "clang"
        source = os.path.join(self.source_folder, "test_pkgconfig.c")
        binary = os.path.join(self.build_folder, "test_pkgconfig")
        cmd = " ".join(shlex.quote(str(arg)) for arg in
                       [cc, "-std=c11", *cflags, source, "-o", binary, *libs])
        self.run(cmd)
        self.run(binary, env="conanrun")
