#!/usr/bin/env python3
"""Conan test_package for dawg 1.2 — 消费者视角验证已安装制品里的 bin/dawg。

验证对象是 `conan create` 安装进包目录的可执行文件（经 conanrun 的 PATH 发现），
不是源码树里的临时产物；断言见 test.sh（golden 逐字节比对、比对结构不变量、
确定性、Seed/GapModel 参数真实接线、四种输出格式、CLI -o 重定向）。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy


class DawgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test.sh", "fixtures/test0.dawg", "fixtures/golden.fasta"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # 独立 build 目录：否则 build_folder == source_folder，测试残留会落进
        # 包源目录（L2/test 阶段的 env 脚本、临时输出等）。
        self.folders.build = "build"

    def generate(self):
        VirtualRunEnv(self).generate(scope="run")

    def build(self):
        copy(self, "test.sh", src=self.source_folder, dst=self.build_folder)
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "fixtures"),
            dst=os.path.join(self.build_folder, "fixtures"),
        )

    def test(self):
        log = os.path.join(self.build_folder, "test.sh.log")
        # OHOS 的 /system/bin/sh(mksh) 不能直接 exec 未签名 ELF，测试脚本统一由
        # bash 驱动（profile 的 buildenv 提供 CONFIG_SHELL）。
        bash = self._bash()
        try:
            self.run(
                f'"{bash}" test.sh > "{log}" 2>&1',
                env="conanrun",
                cwd=self.build_folder,
            )
        except ConanException:
            self.output.error(self._read(log))
            raise
        self.output.info(self._read(log))
        content = self._read(log)
        if "TEST_PACKAGE_RESULT: PASS" not in content:
            raise ConanException(
                "test.sh 未打印汇总行 TEST_PACKAGE_RESULT: PASS（疑似空跑）"
            )

    @staticmethod
    def _read(path):
        if not os.path.isfile(path):
            return f"<missing log: {path}>"
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()

    @staticmethod
    def _bash():
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            shutil.which("bash"),
            "/bin/bash",
            "bash",
        ]
        for candidate in candidates:
            if candidate and (os.path.isabs(candidate) and os.path.isfile(candidate)
                              or not os.path.isabs(candidate)):
                return candidate
        return "sh"
