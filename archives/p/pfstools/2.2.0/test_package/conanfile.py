#!/usr/bin/env python3
"""test_package for pfstools executable set — runs test.sh which invokes the installed binaries.

R34/PF3: 真实执行被测包的 CLI（38 个命令的存在性+可执行性 + PFM->PFS->PFM 往返像素保真 +
pfsgamma 数值正确性 + pfssize/pfscat 尺寸链），非 print-only 空壳。
"""
import os
import shutil
import tempfile

from conan import ConanFile


class PfstoolsTestConan(ConanFile):
    """test_package for pfstools — runs test.sh against installed bin/ tools."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 设备上的 bash 由 CMake find_program(BASH_EXECUTABLE) 实测解析为
        # /data/service/hnp/bin/bash（见 2.2.0/notes.md 未决点②），此处同路径兜底。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        here = getattr(self, "recipe_folder", None) or os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(here, "test.sh")

        # OHOS/HMDFS: conan 以 test_package 目录本身作为 cwd，而该目录刚被写入
        # generators 文件，bash 在其中 getcwd() 失败并打印 shell-init /
        # job-working-directory 噪声（首轮曾因此污染断言输出）。显式切到一个
        # 真实可解析的工作目录再执行；设备 /tmp 只读，故落在 ~/tmp 下。
        try:
            work = tempfile.mkdtemp(prefix="pfstools-tp-",
                                    dir=os.path.join(os.path.expanduser("~"), "tmp"))
        except OSError:
            work = None

        if work is None:
            self.run(f"{bash} \"{script}\"", env="conanrun")
            return
        try:
            self.run(f"{bash} \"{script}\"", env="conanrun", cwd=work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
