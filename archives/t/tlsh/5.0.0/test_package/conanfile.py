#!/usr/bin/env python3
"""Conan test_package — tlsh 5.0.0 消费者验证（L1 smoke + 指纹断言）。

真实链接被测包导出的 tlsh::tlsh 目标，并断言：
  · Tlsh::version() 的版本前缀（产物自报指纹）；
  · 上游 simple_unittest 的已知输入 → 已知 digest（T1 前缀 + 上游 exp 夹具逐字一致）；
  · 距离计算与 fromTlshStr 往返；
并执行安装后的 CLI（bin/tlsh -version），确认命令行产物随包交付且可运行。
"""
import io
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TlshTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv 生成 conanrun 环境（把被测包 bindirs 注入 PATH），
    # 否则 test() 里的 `tlsh -version` 找不到安装后的 CLI
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        # run=True：本包同时交付 CLI（bin/tlsh），test() 需要执行它。
        # 静态库依赖的 require.run 默认为 False，VirtualRunEnv 不会把 bindirs
        # 注入 PATH，`tlsh -version` 会 command not found。
        self.requires(self.tested_reference_str, run=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_tlsh")
        # OHOS: /system/bin/sh (mksh) 不能直接 exec ELF，用 profile 提供的 bash 包裹
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run('"%s" -c \'"%s"\'' % (bash, binary), env="conanrun")
            self._check_cli('"%s" -c "tlsh -version"' % bash)
        else:
            self.run('"%s"' % binary, env="conanrun")
            self._check_cli("tlsh -version")

    def _check_cli(self, command):
        out = io.StringIO()
        self.run(command, env="conanrun", stdout=out)
        text = out.getvalue()
        self.output.info("tlsh -version -> %s" % text.strip())
        assert "5.0.0" in text, "安装的 CLI 未自报 5.0.0：%r" % text
