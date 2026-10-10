#!/usr/bin/env python3
"""Conan test_package — regex-opt 1.2.4

被测对象是打包后的 **regex-opt** 命令行工具（Perl-compatible regular
expression optimizer，Bisqwit）。它读取一个正则表达式并打印等价的优化版本，
例如 `regex-opt 'xaz|xbz|xcz'` -> `x[a-c]z`。实现为纯 C++（main.cc +
libregex.a），不链接任何第三方库，因此 test_package 的消费者直接运行打包
二进制即可，无需 LD_PRELOAD / LD_LIBRARY_PATH 补库。

主配方 package() 已按 E077 对 bin/regex-opt 做 OHOS 自签名（binary-sign-tool
-sign -selfSign 1），test_package 拿到的是已签名、可执行的产物，直接运行。

8 条断言全部真实运行被测二进制并检查退出码与 stdout 内容：
  1-6  已知优化示例：xaz|xbz|xcz -> x[a-c]z；aaa* -> a{2,}；
        (a?){3} -> a{0,3}；xyzyzxyzyz -> (?:x(?:yz){2}){2}；
        a+|aa+ -> a+；dxxxxb|dxxxb|dxxb|dxb -> dx{1,4}b
  7    字符集合并：y|[yp]|[zx] -> [px-z]
  8    非法正则 [abc 必须非零退出并打印 "Error:" 前缀（错误路径断言）

上游套件审计（详见 MANIFEST.yml upstream_test_audit）：regex-opt 1.2.4
发布包共 16 个文件，无 test/ 目录、无 make check/TESTS 目标，README.html 仅
文档与示例 ⇒ upstream_test_total = 0（no_tests）。
"""
import os
import shutil

from conan import ConanFile


class RegexOptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["regex-opt"]
        pkg = dep.package_folder
        binary = os.path.join(pkg, "bin", "regex-opt")

        # HMBS [shell_getcwd]：用注入的 SHELL/CONFIG_SHELL 执行脚本，
        # 不硬编码 /data/service/hnp/bin/bash；脚本为 POSIX sh 兼容。
        shell = (
            os.environ.get("SHELL")
            or os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/bin/sh"
        )
        script = os.path.join(self.source_folder, "test_regexopt.sh")
        cmd = '"{}" "{}" "{}"'.format(shell, script, binary)
        self.run(cmd, env="conanrun")

        # HMBS_TEST_PACKAGE_RESULT 由 test_regexopt.sh 在真实断言结束后打印
        # （discovered/passedCount 来自脚本内部计数）。
        print(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
            '"framework":"none",'
            '"command":"make (no check/test target in upstream Makefile)",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,'
            '"skipped":0,'
            '"reason":"regex-opt 1.2.4 上游无测试套件：发布包 16 个文件无 '
            'test/ 目录、Makefile 仅 all/clean/install（grep -E check|TESTS '
            '为空，无 make check 目标），README.html 仅文档与示例"}'
        )
