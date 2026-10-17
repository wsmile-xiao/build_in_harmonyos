import os

from conan import ConanFile


class PlayumidiTestConan(ConanFile):
    """test_package — 消费者视角：运行安装后的 playumidi 可执行文件（R34 实质依赖被测包）。"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /bin/sh 不存在；由 hnp 提供的 bash 包裹执行（与 CI 侧一致）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
