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
        pkg = self.dependencies["catpoint"].package_folder
        # L0c 门禁：独立测试源文件 + self.run 执行（yarl test_yarl.py
        # 模式）——catpoint 是 ncurses 终端工具，无头环境无法真实运行
        # （'Error opening terminal' 实测，环境阻塞如实说明）；独立脚本
        # 验证二进制存在 + 可执行 + ELF（R34 降级）
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_catpoint.py")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
