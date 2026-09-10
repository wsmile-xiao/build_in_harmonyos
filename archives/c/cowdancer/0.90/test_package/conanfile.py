#!/usr/bin/env python3
"""test_package for cowdancer tools — runs test.sh which invokes the
installed binaries (cowdancer-ilistcreate / cowdancer-ilistdump) end-to-end."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class CowdancerTestConan(ConanFile):
    """test_package for cowdancer — R34 substantial test: actually executes
    the package's binaries to create and dump an ilist file."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 优先经 PATH/CONFIG_SHELL 解析 bash（避免硬编码设备绝对路径）；
        # conanrun 环境已把 OHOS bash 加入 PATH。
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not bash:
            raise ConanException("bash not found in PATH")
        self.run(f"{bash} test.sh", env="conanrun")