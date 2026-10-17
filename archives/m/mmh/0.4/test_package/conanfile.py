import os

from conan import ConanFile


class MmhTestConan(ConanFile):
    """test_package for mmh — runs test.sh (smoke) and test_e2e.sh (full
    consumer e2e: maildrop incorporation -> scan/pick -> MIME list/store ->
    refile) against the installed CLI. Both scripts are launched through
    bash because on OHOS the kernel refuses shebang-script execve and
    /system/bin/sh cannot host the test harness reliably."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: 内核拒绝 shebang 脚本 execve（rc 126）。
        # 用 bash 包装测试脚本执行。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
        # 鸿蒙特有测试——完整消费者端到端用例（8 例全链路，见 test_e2e.sh）
        self.run(f"{bash} test_e2e.sh", env="conanrun")
