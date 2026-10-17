#!/usr/bin/env python3
"""Conan test_package — xclip 0.13.1 L1 测试

R34: test_package 必须实质依赖被测包。
- test.c 执行 xclip -version 校验版本输出（任何环境可跑的保底测试）；
- 上游 xctest 60 场景（5 数据量 × 4 selections × 3 模式）集成：检测/启动 X server
  （优先 DISPLAY，其次系统 Xvfb），可用则实际运行全部场景；无 X server 时按
  平台限制降级说明（与仓库内 xterm 同款处理），不阻塞构建。
"""
import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XclipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d: 必须通过 self.run 实质执行测试二进制（xclip -version 校验，任何环境可跑）
        cmake = CMake(self)
        cmake.test()
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_xclip")
        self.run(test_bin, env="conanrun")

        # —— 上游 xctest 60 场景集成（需 X server）——
        pkg_bin = os.path.join(self.dependencies["xclip"].package_folder, "bin")
        xclip_bin = os.path.join(pkg_bin, "xclip")
        if not os.path.isfile(xclip_bin):
            self.output.info("xclip binary not found at %s; xctest skipped" % xclip_bin)
            return
        # xctest 脚本用 ./xclip（相对路径），复制 xclip 与脚本到工作目录
        workdir = os.getcwd()
        shutil.copy(xclip_bin, os.path.join(workdir, "xclip"))
        shutil.copy(os.path.join(self.source_folder, "xctest"), os.path.join(workdir, "xctest"))
        os.chmod(os.path.join(workdir, "xctest"), 0o755)

        # 检测/启动 X server：优先 DISPLAY，其次系统 Xvfb
        display = os.environ.get("DISPLAY", "").strip()
        xvfb_proc = None
        if not display:
            xvfb = shutil.which("Xvfb")
            if xvfb:
                xvfb_proc = subprocess.Popen(
                    [xvfb, ":99", "-screen", "0", "1024x768x24", "-ac"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                time.sleep(3)
                display = ":99"
            else:
                # 无 X server（平台限制，与仓库内 xterm 同款处理）
                self.output.info(
                    "无 X server（DISPLAY 为空且无 Xvfb）: xctest 60 场景按平台限制跳过；"
                    "xclip -version 保底测试已通过"
                )
                return
        env_display = dict(os.environ)
        env_display["DISPLAY"] = display
        env_display["TMPDIR"] = os.environ.get("TMPDIR", workdir)
        try:
            proc = subprocess.run(
                ["./xctest"], cwd=workdir, capture_output=True, text=True,
                timeout=300, env=env_display,
            )
            if proc.returncode != 0:
                raise Exception("xctest failed rc=%d: %s" % (proc.returncode, proc.stderr[-800:]))
            self.output.info("上游 xctest 60 场景全部通过 (rc=0)")
        finally:
            if xvfb_proc is not None:
                xvfb_proc.terminate()
                time.sleep(1)
