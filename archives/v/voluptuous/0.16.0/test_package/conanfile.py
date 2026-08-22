from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["voluptuous"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        # L0c + R34 合规：独立测试源文件（test_voluptuous.py——真实调用
        # 被测库 API——voluptuous.Schema 数据校验）+ self.run 执行
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_voluptuous.py")
        self.run(
            f"PYTHONPATH='{site}' python3 '{test_script}' '{site}'",
            env="conanrun")
