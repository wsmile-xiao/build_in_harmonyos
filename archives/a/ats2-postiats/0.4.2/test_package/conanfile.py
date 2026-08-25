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
        pkg = self.dependencies["ats2-postiats"].package_folder
        bindir = os.path.join(pkg, "usr", "local", "bin")
        patshome = os.path.join(pkg, "usr", "local", "lib",
                                "ats2-postiats-0.4.2")
        # L0c + R34 合规：独立测试源文件（test_ats2.py——真实调用被测
        # 编译器 patscc 编译+运行最小 ATS 程序）+ self.run 执行
        test_script = os.path.join(os.path.dirname(__file__), "test_ats2.py")
        self.run(f"python3 '{test_script}' '{bindir}' '{patshome}'",
                 env="conanrun")
