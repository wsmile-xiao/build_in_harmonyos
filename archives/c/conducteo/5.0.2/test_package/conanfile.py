import os

from conan import ConanFile


class ConducteoTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution. 优先取 CONFIG_SHELL（CI profile
        # buildenv 注入），未设置时回退到 worker 已知的 bash 路径
        # （与 acetoneiso 同款做法，本机/CI 均为 /data/service/hnp/bin/bash）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")