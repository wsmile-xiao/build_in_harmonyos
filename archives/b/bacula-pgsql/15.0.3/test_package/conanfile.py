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
        pkg = self.dependencies["bacula-pgsql"].package_folder
        # L0c 门禁：独立测试源文件 + self.run 执行（yarl test_yarl.py
        # 模式）——libbaccats-postgresql 运行需 PostgreSQL server（OHOS
        # 无，环境阻塞如实说明）；独立脚本验证后端库存在 + ELF（R34 降级）
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_bacula.py")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
