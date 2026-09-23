import os
import shlex

from conan import ConanFile


class OdinfmtTestConan(ConanFile):
    """test_package for odinfmt — 调用 run_tests.sh，用包内 odinfmt 真实格式化
    固定输入源文件并做逐字节断言（文件 / 幂等 / stdin / -w 写回 / CLI 契约 共 5 项）。"""
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["odinfmt"].package_folder
        odinfmt = os.path.join(pkg, "bin", "odinfmt")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "run_tests.sh")
        q = shlex.quote
        # 5 项检查（CLI 契约 / 文件模式 diff / 幂等 / stdin / -w 写回）全在 run_tests.sh 内实现
        cmd = " ".join([q(bash), q(script), q(odinfmt), q(pkg), q(self.build_folder)])
        self.run(cmd)
