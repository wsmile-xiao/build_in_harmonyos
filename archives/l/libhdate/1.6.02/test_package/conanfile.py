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
        pkg = self.dependencies["libhdate"].package_folder
        # L0c 合规：独立测试源文件 + self.run 执行（yarl test_yarl.py
        # 模式）——hdate 希伯来历法日期计算在 OHOS 可真实运行（无环境
        # 限制）——真实执行 + 库/头文件验证（R34）
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_libhdate.py")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
