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
        pkg = self.dependencies["cdargs"].package_folder
        # L0c 门禁：独立测试源文件 + self.run 执行（calcurse test_calcurse.py
        # 模式）。cdargs -f <list> -a <absdir> 是非交互书签添加（源码中
        # -a/--add 分支在 init_curses() 之前 exit），可无头真实运行验证。
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_cdargs.py")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
