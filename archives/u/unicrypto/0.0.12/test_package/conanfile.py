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
        pkg = self.dependencies["unicrypto"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        tp_dir = os.path.dirname(__file__)
        # L0c + R34 合规：独立测试源（test_unicrypto.py——真实调用被测库 API，
        # 内置 HMBS_TEST_PACKAGE_RESULT 标记）+ self.run 执行
        smoke = os.path.join(tp_dir, "test_unicrypto.py")
        upstream = os.path.join(tp_dir, "run_upstream_tests.py")
        upstream_tests = os.path.join(tp_dir, "upstream_tests")
        self.run(f"python3 '{smoke}' '{site}'", env="conanrun")
        # 上游测试接入（run_upstream_tests.py 内置 HMBS_UPSTREAM_TEST_RESULT
        # 标记，直接执行纯后端子集，不依赖已安装的 pytest——OHOS 无 pytest）
        if os.path.exists(upstream):
            self.run(f"python3 '{upstream}' '{site}' '{upstream_tests}'",
                     env="conanrun")
