#!/usr/bin/env python3
"""Consumer test for paraglob/0.6.0 —— L1 消费者测试（鸿蒙特有测试 11 条）。

两条独立消费路径，全部经 `self.run(..., env="conanrun")` 真实执行
（PF3 / R34 / conan-verify 均以 self.run 为唯一认可形态）：

  1) 库消费者 test_paraglob —— 通过 CMakeDeps `find_package(paraglob)`
     链接安装后的 libparaglob.a + 头文件，跑 A1-A5 + A6a/A6b 共 7 条 API 断言；
  2) CLI 消费者 test_cli.sh —— 直跑安装后的 bin/paraglob-test，
     跑 C1-C4 共 4 条断言（期望值逐条对齐上游 btest Baseline）。

断言合计 7+4=11 条 = PR 正文「鸿蒙特有测试」行取数。
cwd 为 cmake_layout 的 build 目录（先例 #5），因此所有脚本/产物一律
以绝对路径传参，不依赖 cwd。
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ParaglobTestConan(ConanFile):
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

    def test(self):
        if not can_run(self):
            self.output.info("Skipping run of consumer binary in cross-build")
            return

        # ── 1) 库消费者：A1-A5 + A6a/A6b（7 条） ──────────────────
        exe = os.path.join(self.build_folder,
                           self.cpp.build.bindirs[0], "test_paraglob")
        if not os.path.isfile(exe):
            raise Exception(f"消费者可执行文件未生成: {exe}")
        self.run(f'"{exe}"', env="conanrun")

        # ── 2) CLI 消费者：C1-C4（4 条） ────────────────────────
        script_src = os.path.join(self.source_folder, "test_cli.sh")
        script = os.path.join(self.build_folder, "test_cli.sh")
        shutil.copy(script_src, script)
        # HMDFS 可执行位不持久（device-facts §一.27）→ 显式补一次再显式解释器执行
        os.chmod(script, os.stat(script).st_mode | stat.S_IXUSR)
        bindir = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "bin")
        self.run(f'{self._shell()} "{script}" "{bindir}"', env="conanrun")

    @staticmethod
    def _shell():
        # 设备无 /bin/bash（device-facts §一.16），且 toybox sh 对部分
        # bashism 有解析缺陷（§一.19/26）；本脚本按 POSIX 写，优先用
        # HNP bash 其次 /bin/sh。
        for candidate in ("/data/service/hnp/bin/bash", "/bin/sh", "sh"):
            if os.path.isfile(candidate):
                return candidate
        return "sh"
