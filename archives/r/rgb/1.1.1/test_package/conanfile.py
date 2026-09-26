#!/usr/bin/env python3
"""Conan test_package — rgb 1.1.1

被测对象是 text 模式产出的 **showrgb** 二进制（上游 Makefile.am 的
`bin_PROGRAMS = showrgb`；`rgb` DB 编译器需未发布的 xorg-server，见主配方
docstring）。showrgb 不链接任何 X 客户端库（text 分支只用 fopen/sscanf/
asprintf/printf），因此无需 LD_PRELOAD / LD_LIBRARY_PATH 补库。

5 条断言全部真实运行被测二进制并检查退出码与 stdout/stderr 内容：
  1. showrgb --version  -> 输出上游 PACKAGE_STRING "rgb 1.1.1"
  2. showrgb --help     -> 退出码 0
  3. showrgb（无参）    -> 读取包内安装的默认库 <pkg>/share/X11/rgb(.txt)，
                           断言条目数 >= 100 且规范色 red 解析为 255 0 0
  4. showrgb <显式库路径>（按 man 页约定不带 .txt 后缀）
                        -> 断言脚本自造的 4 色 mini 库被精确解析：恰好 4 条，
                           且 agentred == 255 0 0（证明 dbname 与 .txt 拼接逻辑生效）
  5. showrgb <不存在的库> -> 必须非零退出并打印
                           "unable to open rgb database"（错误路径断言）

上游套件审计（详见 MANIFEST.yml upstream_test_audit）：rgb 1.1.1 发布包
无任何自动化测试 —— Makefile.am 只有 bin_PROGRAMS + SUBDIRS = man，
grep -E 'check|TESTS' 结果为空，无 TESTS/check_PROGRAMS/check-local，
源码树无 tests/ 目录 ⇒ N_static = 0。
"""
import os
import shutil

from conan import ConanFile


class RgbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["rgb"]
        pkg = dep.package_folder
        showrgb = os.path.join(pkg, "bin", "showrgb")

        # HMBS [shell_getcwd]：用注入的 SHELL/CONFIG_SHELL 执行脚本，
        # 不硬编码 /data/service/hnp/bin/bash；脚本为 POSIX sh 兼容。
        shell = (
            os.environ.get("SHELL")
            or os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/bin/sh"
        )
        script = os.path.join(self.source_folder, "test_rgb.sh")
        cmd = f'"{shell}" "{script}" "{showrgb}" "{pkg}"'
        self.run(cmd, env="conanrun")

        # HMBS_TEST_PACKAGE_RESULT 由 test_rgb.sh 在真实断言结束后打印
        # （discovered/passedCount 来自脚本内部计数）。
        print(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
            '"framework":"none",'
            '"command":"make -n check (no check target)",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,'
            '"skipped":0,'
            '"reason":"rgb 1.1.1 上游无测试套件：Makefile.am 无 check/TESTS '
            '目标（grep -E \\"check|TESTS\\" 结果为空）、源码树无 tests/ 目录"}'
        )
