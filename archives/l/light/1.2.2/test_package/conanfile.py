import os

from conan import ConanFile


class LightTestConan(ConanFile):
    """test_package for the `light` executable — runs test.sh against the installed binary."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 包装环境，统一用 bash 起 test.sh。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(bash + " test.sh", env="conanrun")
