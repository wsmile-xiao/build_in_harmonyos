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
        pkg = self.dependencies["ats2-lang"].package_folder
        libdir = os.path.join(pkg, "lib")
        patshome = os.path.join(pkg, "include", "ats2")
        # L0c + R34 合规：独立测试源文件（test_ats2_lang.py——真实使用
        # 打包的 libats 运行时）+ self.run 执行
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_ats2_lang.py")
        self.run(f"python3 '{test_script}' '{patshome}' '{libdir}'",
                 env="conanrun")
