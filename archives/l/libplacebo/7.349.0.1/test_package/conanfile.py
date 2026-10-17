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
        pkg = self.dependencies["libplacebo"].package_folder
        # L0c 合规：独立测试源文件 + self.run 执行（yarl test_yarl.py
        # 模式）——libplacebo 视频渲染需 GPU/显示（OHOS 无，环境阻塞如实
        # 说明）；独立脚本验证库存在 + ELF + 头文件（R34 降级）
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_libplacebo.py")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
