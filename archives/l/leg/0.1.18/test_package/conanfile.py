import os
import shutil

from conan import ConanFile


class LegTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 包是 application 类型：消费者验证 = 直接用包安装出来的 peg / leg
        # 两个命令干活。test.sh 内部用 set -e 与 grep -q 断言，退出码即结论。
        # CONFIG_SHELL 由 OHOS profile 的 buildenv 提供（与 peg/0.1.19 一致）；
        # 在没设该变量的 Linux 开发机上回落到 PATH 里的 bash，便于本地自检。
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        self.run(f"{bash} test.sh", env="conanrun")
