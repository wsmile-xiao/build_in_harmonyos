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
        pkg = self.dependencies["calcurse"].package_folder
        # L0c 门禁：独立测试源文件 + self.run 执行（yarl test_yarl.py
        # 模式）——calcurse 是 ncurses 终端 UI，无头环境无法初始化终端
        # （同 catpoint 的 'Error opening terminal'，环境阻塞如实说明）；
        # 上游 make check（71/72）已在 build() 实测回填；独立脚本验证
        # 二进制存在 + 可执行 + ELF（R34 降级）
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_calcurse.py")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
