import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class CdoTestConan(ConanFile):
    """test_package for cdo executable — runs test.sh which exercises the cdo binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 交叉编译环境（WSL）无法执行 aarch64-musl 产物，消费者测试交给 CI/鸿蒙电脑执行；
        # 与 plod 等先例一致，此处不做假通过。
        if not can_run(self):
            self.output.info("Cross build: cdo consumer test deferred to CI/HarmonyOS host")
            return
        # OHOS: /system/bin/sh (mksh) 执行 ELF 不稳定，用 bash 包装（与 aa3d 先例一致）
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/bin/bash"
        self.run(f"{bash} test.sh", env="conanrun")
