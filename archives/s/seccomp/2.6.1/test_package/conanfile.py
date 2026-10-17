#!/usr/bin/env python3
"""Test package for seccomp (libseccomp) on HarmonyOS PC.

Consumer verification (R34): compile a C program that really calls
libseccomp's user-space API seccomp_version()/seccomp_api_get(), then
run it. Linked-program execution is used (not ctypes dlopen, which the
CI el2 sandbox rejects with Permission denied).
"""
from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["seccomp"].package_folder
        # L0c + R34 合规：独立测试源文件（test_seccomp.c——真实调用
        # seccomp_version()/seccomp_api_get() 纯用户态 API）+ self.run
        # 编译链接运行（**不用 ctypes dlopen——CI el2 沙箱 dlopen 拒绝
        # Permission denied 实测**；链接程序运行由动态链接器加载，沙箱允许）
        src = os.path.join(os.path.dirname(__file__), "test_seccomp.c")
        exe = "/data/storage/el2/base/cache/seccomp-tp-test"
        self.run(
            f"/data/service/hnp/bin/clang '{src}' "
            f"-I'{pkg}/include' -L'{pkg}/lib' -lseccomp -o '{exe}'",
            env="conanrun",
        )
        self.run(f"'{exe}'", env="conanrun")
