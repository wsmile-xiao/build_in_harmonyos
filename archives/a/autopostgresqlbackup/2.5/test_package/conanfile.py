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
        pkg = self.dependencies["autopostgresqlbackup"].package_folder
        # L0c + R34 合规：独立测试源文件（test_autopostgresqlbackup.sh——
        # 真实执行脚本（bash -n 语法 + 运行 rc 校验——备份运行需
        # PostgreSQL 服务器（OHOS 受限——环境限制如实，非跳过））+
        # self.run 执行
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_autopostgresqlbackup.sh")
        self.run(
            f"sh '{test_script}' '{pkg}/bin/autopostgresqlbackup'",
            env="conanrun")
