#!/usr/bin/env python3
"""test_package for tiv 1.2.1 — 通过 conanrun PATH 实际运行打包后的二进制。"""
import os
import shlex

from conan import ConanFile


class TivTestConan(ConanFile):
    """test_package for tiv executable — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 把依赖包的 package_folder 传给 test.sh：脚本据此断言 PATH 上的 tiv
        # 就是本包 bin/ 里的那个文件，而不是宿主上碰巧同名的别的 tiv。
        pkg_dir = self.dependencies[self.tested_reference_str].package_folder
        self.run(f"TIV_PKG_DIR={shlex.quote(pkg_dir)} {bash} test.sh", env="conanrun")