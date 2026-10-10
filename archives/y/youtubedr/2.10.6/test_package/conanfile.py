#!/usr/bin/env python3
"""Conan test_package for youtubedr 2.10.6 — CLI tool verification.

youtubedr 是命令行工具（application）。本测试验证 bin/youtubedr 已安装且可执行：
test.sh 跑 `youtubedr version`（断言输出含 2.10.6 与 Version 字段）与
`youtubedr --help`（断言输出 cobra help 行 "for more information about a command"），
共 3 项实质断言。
按 astroterm/abuild-sudo 先例，在 test() 内输出 HMBS_TEST_PACKAGE_RESULT
硬门禁标记，discovered/passedCount = 本 test_package 的真实断言数。
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class YoutubedrTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["youtubedr"].package_folder
        exe_name = "youtubedr.exe" if str(self.settings.os) == "Windows" else "youtubedr"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"youtubedr binary not found: {bin_path}"

        if not can_run(self):
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"youtubedr is not an ELF binary: {magic!r}"
            self.output.info(f"youtubedr binary exists and has ELF magic: {bin_path}")
            return

        test_script = os.path.join(self.recipe_folder, "test.sh")
        # OHOS HMFS/HMDFS 无法 getcwd conan 构建目录；按 HMBS 平台诊断用注入的
        # /bin/sh（而非 HNP bash）执行 POSIX test.sh，脚本内部会 cd 到可 getcwd 目录。
        test_cmd = f'sh "{test_script}" "{bin_path}"'
        # 3 explicit checks in test.sh (version->2.10.6, version->Version,
        # --help->cobra help "for more information about a command")
        # test.sh 把真实 total/passed 写到结果文件（TMPDIR 优先），此处在 run 后读回，
        # 生成一致标记：discovered=total、passedCount=passed。不再硬编码 passedCount=3。
        result_dir = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.build_folder
        result_file = os.path.join(result_dir, "youtubedr_test_package_result.txt")
        os.environ.setdefault("TEST_PACKAGE_RESULT_FILE", result_file)

        run_error = None
        try:
            self.run(test_cmd, env="conanrun")
        except Exception as exc:  # noqa: BLE001 - captured, marker still emitted below
            run_error = exc

        total = 3
        passed = 0
        if os.path.isfile(result_file):
            with open(result_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("total="):
                        try:
                            total = int(line.split("=", 1)[1])
                        except ValueError:
                            pass
                    elif line.startswith("passed="):
                        try:
                            passed = int(line.split("=", 1)[1])
                        except ValueError:
                            pass

        test_pkg = {
            "executed": True,
            "passed": (run_error is None) and (total > 0) and (passed == total),
            "command": test_cmd,
            "discovered": total,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
        )
        if run_error is not None:
            raise run_error

