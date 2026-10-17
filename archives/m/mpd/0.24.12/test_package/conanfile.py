#!/usr/bin/env python3
"""Conan test_package for mpd 0.24.12 — 消费者测试 C1-C3（R40 实质验证）。

C1: mpd --version（版本信息）
C2: 配置解析 + 守护进程启动 + HTTP API 监听 + 曲库扫描导入
C3: 解码后端初始化（run_decoder 经 ffmpeg 后端解码 wav）

test_mpd.sh 为纯 shell 断言脚本（真实失败路径非零退出，无硬编码通过）。
"""
import os

from conan import ConanFile


class MPDTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["mpd"]
        pkg_dir = dep.package_folder
        script = os.path.join(self.recipe_folder, "test_mpd.sh")
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f"{bash} {script} {pkg_dir}", env="conanrun")
        else:
            self.run(f"sh {script} {pkg_dir}", env="conanrun")
