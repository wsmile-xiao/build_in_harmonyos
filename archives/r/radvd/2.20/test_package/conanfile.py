import os

from conan import ConanFile


class RadvdTestConan(ConanFile):
    """test_package for radvd 2.20 — 消费者视角执行被测包安装出来的两个二进制。

    R34：这里的每一条断言都真的跑 radvd / radvdump 本身（把它们改名就会失败），
    不是打印字符串的空壳。CI 的 L1e 破坏性反向验证（移走产物目录后 conan test
    必须转失败）因此天然成立。
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS 的 /bin/sh 不保证存在（R5/§2 ADAPTATION_GUIDE），用 profile
        # [buildenv] 里的 CONFIG_SHELL 包裹脚本执行。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
