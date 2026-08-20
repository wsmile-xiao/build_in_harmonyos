#!/usr/bin/env python3
"""Conan test_package for google-authenticator-libpam — 消费者视角验证。

验证：
1. bin/google-authenticator 可执行文件存在
2. --help / --version 能正常输出（L2 冒烟测试）
3. lib/security/pam_google_authenticator.so PAM 模块产物存在
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class GoogleAuthenticatorLibpamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _package_paths(self):
        pkg = self.dependencies["google-authenticator-libpam"].package_folder
        return pkg, os.path.join(pkg, "bin", "google-authenticator"), os.path.join(
            pkg, "lib", "security", "pam_google_authenticator.so")

    def test(self):
        pkg, cli, module = self._package_paths()
        cli_ok = os.path.isfile(cli)
        module_ok = os.path.isfile(module)
        self.output.info(f"google-authenticator CLI found: {cli_ok} ({cli})")
        self.output.info(f"pam_google_authenticator.so found: {module_ok} ({module})")

        if not cli_ok or not module_ok:
            raise Exception("package artifacts missing (CLI or PAM module)")

        if can_run(self):
            self.run(f"{cli} --help", env="conanrun")
            # 运行测试源脚本（src/test_google_authenticator.sh，L0c 门禁要求
            # test_package/ 下有 .c/.cpp/.sh/.py 测试源文件）
            script = os.path.join(self.source_folder, "src", "test_google_authenticator.sh")
            if os.path.isfile(script):
                # 沙箱导出可能丢失可执行位，显式用 bash 调用
                self.run(f'bash "{script}" "{cli}"', env="conanrun")
            self.run(f"{cli} --version", env="conanrun")
        else:
            self.output.info("Cross-building: skipping runtime invocation, artifacts verified")
