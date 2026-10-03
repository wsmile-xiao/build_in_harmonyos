import os

from conan import ConanFile


class CscopeTestConan(ConanFile):
    """test_package for cscope — runs test.sh which exercises the real CLI
    (version banner + build a cross-reference db and run a line-mode query)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
        # 鸿蒙特有测试——完整消费者端到端用例（7 例全链路，见 test_e2e.sh）
        self.run(f"{bash} test_e2e.sh", env="conanrun")
