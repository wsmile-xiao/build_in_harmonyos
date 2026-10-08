import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["beniget"].package_folder
            # 复发包内持久化的上游测试结果（缓存命中轮次 build() 被跳过，
            # 只有 marker 能证明上游套件真实执行过；L1c 亦据此判定）。
            marker = os.path.join(pkg, "res", "upstream_test_result.json")
            if os.path.isfile(marker):
                with open(marker, encoding="utf-8") as fh:
                    self.output.info("HMBS_UPSTREAM_TEST_RESULT=%s"
                                     % fh.read().strip())
            else:
                self.output.warning("[beniget] upstream marker missing: %s"
                                    % marker)
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_beniget.py")
            # 沙箱 PATH 无 python3——绝对路径（同 packaging 教训）
            import sys
            py = "/data/service/hnp/bin/python3" \
                if os.path.isfile("/data/service/hnp/bin/python3") \
                else sys.executable
            self.run(f'{py} "{test_script}" "{pkg}"', env="conanrun")
