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
        pkg = self.dependencies["backup2l"].package_folder
        # L0c 门禁：独立测试源文件 + self.run 执行（yarl test_yarl.py
        # 模式）——backup2l 运行需已编辑配置文件（first-time.conf 模板
        # UNCONFIGURED=1，工具使用前提如实说明）；独立脚本验证脚本存在
        # + bash -n 语法检查
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_backup2l.py")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
