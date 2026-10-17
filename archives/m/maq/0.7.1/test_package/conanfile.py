#!/usr/bin/env python3
"""Conan test_package for maq 0.7.1。

maq 是 CLI 工具（application），不提供库/头文件，因此这里驱动安装后的
`maq` 可执行文件跑一遍真实流程（fasta2bfa → fastq2bfq → map(PE) → assemble
→ mapstat），并校验输出的 .bfa/.bfq/.map/.cns 文件非空、内容可解析。
"""
import os
import shutil

from conan import ConanFile


class MaqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) 不能直接 exec ELF；上游脚本用 bash 驱动。
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_maq.sh")
        self.run(f'"{bash}" "{script}"', env="conanrun")
