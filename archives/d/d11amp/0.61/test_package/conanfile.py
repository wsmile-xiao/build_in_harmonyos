#!/usr/bin/env python3
"""Conan test_package for d11amp — CLI 实机验证 (R34).

d11amp 是 GTK4 图形 mp3 播放器，test_package 做两件事：
1. 运行安装后的 d11amp --version，断言输出版本号 0.61
2. 运行 d11amp --help，断言帮助输出可读

（上游 checks.mk 的主题转储校验依赖图形栈，探索编译阶段已在设备实测
  check OK；test_package 以 CLI 断言覆盖安装产物的可执行性。）
"""
import os
from glob import glob

from conan import ConanFile


class D11AmpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os == "OHOS":
            # 与 audiowmark/gtkmm 先例同款：OHOS 动态库（含 libc++_shared.so）
            # 在 SDK 的 llvm/lib/aarch64-linux-ohos 目录，加载器默认不搜该路径。
            # 注入 LD_LIBRARY_PATH 以解析 libharfbuzz.so.0 等的 C++ runtime 依赖。
            sdk_lib = os.environ.get("OHOS_SDK_LIB")
            if not sdk_lib:
                candidates = glob(
                    "/data/service/hnp/ohos-sdk.org/*/"
                    "ohos/native/llvm/lib/aarch64-linux-ohos"
                )
                if candidates:
                    sdk_lib = candidates[0]
            if sdk_lib:
                os.environ["LD_LIBRARY_PATH"] = (
                    sdk_lib
                    + os.pathsep
                    + os.environ.get("LD_LIBRARY_PATH", "")
                )
        # OHOS /system/bin/sh (mksh) 无法执行 ELF；用 bash 驱动测试脚本
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")