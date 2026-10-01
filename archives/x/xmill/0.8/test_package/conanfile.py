import os

from conan import ConanFile


class XmillTestConan(ConanFile):
    """test_package for the xmill application package.

    被测物是包内的两个可执行文件 ``bin/xmill``（压缩器）与 ``bin/xdemill``（解压器）。
    ``test.sh`` 实际调用这两个二进制做压缩/解压回环并逐项判定，不是打印空壳。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 二进制，用 bash 包裹
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
