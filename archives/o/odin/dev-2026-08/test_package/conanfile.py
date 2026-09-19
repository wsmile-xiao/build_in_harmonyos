import os
import shlex

from conan import ConanFile


class OdinTestConan(ConanFile):
    """test_package for odin — 调用 run_tests.sh，用包内 odin 编译器真实编译并运行 Odin 源程序。"""
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["odin"].package_folder
        odin = os.path.join(pkg, "bin", "odin")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "run_tests.sh")
        q = shlex.quote
        # 3 项检查（version 断言 / hello 编译并运行 / 自举验证）全部在 run_tests.sh 内实现
        cmd = " ".join([q(bash), q(script), q(odin), q(pkg), q(self.build_folder)])
        self.run(cmd, env="conanrun")
