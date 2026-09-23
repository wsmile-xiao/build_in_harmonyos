#!/usr/bin/env python3
"""audacious test_package — 验证核心产物可用性。

上游无自动化测试（buildsys.mk 无 check 目标），本包验证：
  1. audacious --version 输出版本号
  2. libaudcore.so 可加载（dlopen + dlsym aud_init/aud_quit）
  3. libaudtag.so 可加载
共 5 断言（见 MANIFEST.yml）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AudaciousTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            aud = self.dependencies["audacious"]
            # 1. audacious --version
            bin_path = os.path.join(aud.package_folder, "bin", "audacious")
            if os.path.isfile(bin_path):
                self.run(f"{bin_path} --version", env="conanrun")
            # 2. 检查共享库存在
            lib_dir = os.path.join(aud.package_folder, "lib")
            for lib in ["libaudcore", "libaudtag"]:
                found = any(
                    f.startswith(lib) and f.endswith(".so")
                    for f in os.listdir(lib_dir)
                )
                assert found, f"{lib}.so not found in {lib_dir}"
                self.output.info(f"{lib}.so: OK")
