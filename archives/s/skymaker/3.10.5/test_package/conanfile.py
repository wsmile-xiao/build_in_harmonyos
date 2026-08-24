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
        pkg = self.dependencies["skymaker"].package_folder
        bindir = os.path.join(pkg, "bin")
        # L0c + R34 合规：独立测试源文件（test_skymaker.py——真实调用
        # 被测 CLI）+ self.run 执行
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_skymaker.py")
        self.run(f"python3 '{test_script}' '{bindir}'", env="conanrun")
