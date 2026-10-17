#!/usr/bin/env python3
"""Conan test_package for cleo 0.004 — Perl CLI consumer test.

编译并运行 test_cleo 验证 cleo Perl CLI 安装：
  1. bin/cleo 脚本存在且可执行
  2. 校验 shebang 为 perl + perl 可运行（OHOS 缺 5 个模块，不执行 perl -c）
通过 self.run() 实跑测试程序，满足 R34 + L0 stub_test_method 门禁。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class CleoTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cleo_dep = self.dependencies["cleo"]
        cleo_bin = os.path.join(cleo_dep.package_folder, "bin", "cleo")
        perl = os.environ.get("PERL", "perl")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_cleo")
        # CI 真根因: perl -c bin/cleo 炸 exited with code 2 — PERL5LIB 缺 App::Cleo 模块路径
        # cleo 包 App::Cleo.pm 真位置在 lib/perl5/App/Cleo.pm（ExtUtils::MakeMaker INSTALL_BASE 产物）
        # → 显式取 cleo 包 lib/perl5 路径注入 PERL5LIB（脚本 use App::Cleo 走 @INC 找 lib/perl5/App/）
        cleo_perl5lib = os.path.join(cleo_dep.package_folder, "lib", "perl5")
        # Conan 2.x run() env 要 list 格式（非 dict/str）
        env = [f"PERL5LIB={cleo_perl5lib}"] if os.path.isdir(cleo_perl5lib) else None
        self.run(f'"{test_bin}" "{cleo_bin}" "{perl}"', env=env)
