import os

from conan import ConanFile


class AcedbTestConan(ConanFile):
    """test_package for acedb — executable package, runs test.sh which invokes the binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        # stdin 重定向 /dev/null：mddriver 无参数时从 stdin 读数据（fread 直到 EOF），
        # CI 上 stdin 非 EOF 会永久阻塞挂起测试，故强制 </dev/null。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh < /dev/null", env="conanrun")
