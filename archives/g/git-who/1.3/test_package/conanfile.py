#!/usr/bin/env python3
"""Conan test_package — git-who 1.3 (Go CLI tool, executable package).

test.sh 真实调用被测二进制（--version / --help / 临时 git 仓库上的
`git-who table`），自身输出 HMBS_TEST_PACKAGE_RESULT 机器证据标记
（discovered=3/passedCount 来自脚本实际计数），经 self.run 透传进
conan/preflight 日志供 hmbs 采集。

HMBS_UPSTREAM_TEST_RESULT：上游 go 测试在 recipe build() 内真机执行，
结果写入包内 res/upstream_test_result.json（真实计数）。预检复用时
conan 缓存可能跳过 build()，故本阶段读取该文件并裸 print 复发标记。
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class GitWhoTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["git-who"].package_folder
        bin_path = os.path.join(package_folder, "bin", "git-who")
        assert os.path.isfile(bin_path), f"git-who binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            # HMBS injects SHELL=/bin/sh; avoid hard-coded `bash` which on
            # HNP lives under /data/service/hnp/bin/bash and can fail getcwd
            # on HMFS. Run the script from a writable cwd (TMPDIR, injected
            # by HMBS) instead of the HMDFS package folder.
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run(f'"{shell}" "{test_script}" "{bin_path}"', env="conanrun", cwd=cwd)
            # HMBS_TEST_PACKAGE_RESULT 由 test.sh 在用例结束后自行输出
            # （discovered/passedCount 为真实计数），此处不再重复输出。
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"git-who is not an ELF binary: {magic!r}"
            self.output.info(f"git-who binary exists and has ELF magic: {bin_path}")

        # Re-emit the upstream go-test result recorded by build() on the real
        # device. The marker must appear in every preflight log; conan cache
        # reuse skips build(), so this always-running phase is the reliable
        # channel (same pattern as aribb24/1.0.4).
        result_file = os.path.join(package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_file):
            raise ConanException(
                f"upstream_test_result.json missing in package: {result_file} — "
                "build() must have failed to persist the upstream test result")
        with open(result_file, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(upstream, ensure_ascii=False)}", flush=True)
