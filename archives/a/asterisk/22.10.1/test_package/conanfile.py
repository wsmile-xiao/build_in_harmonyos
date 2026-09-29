#!/usr/bin/env python3
"""Conan test_package — asterisk 22.10.1 (application package).

被测包是应用程序而非库，无法以链接方式消费；按 R34 以「执行被打包的
二进制」作为实质测试：断言主程序与 LDAP 模块存在，并实际运行
`asterisk -V` 验证可执行（ELF 已在 package() 中签名）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AsteriskTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["asterisk"].package_folder
        asterisk_bin = os.path.join(pkg, "sbin", "asterisk")
        assert os.path.isfile(asterisk_bin), f"missing main binary: {asterisk_bin}"
        ldap_mod = os.path.join(
            pkg, "lib", "asterisk", "modules", "res_config_ldap.so")
        assert os.path.isfile(ldap_mod), f"missing LDAP module: {ldap_mod}"
        if not can_run(self):
            self.output.info("cross-compiling (can_run=False): verified files exist, skip running asterisk -V")
            self.output.info(f"  verified: {asterisk_bin}")
            self.output.info(f"  verified: {ldap_mod}")
            return
        self.output.info("running packaged asterisk -V ...")
        # 包已自包含（依赖库捆绑进 lib/ 并签名，RUNPATH 指向包内 lib/），
        # 直接运行即可；L0d 门禁要求 test() 含 self.run 字面量，故使用 self.run
        # 真实执行二进制并校验输出（退出码非 0 时 self.run 自动失败）。
        output_file = os.path.join(self.build_folder, "asterisk_version.txt")
        self.run(f'"{asterisk_bin}" -V > "{output_file}" 2>&1', env="conanrun")
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            output = f.read()
        self.output.info(f"asterisk -V output: {output.strip()}")
        assert "Asterisk" in output, f"asterisk -V output missing 'Asterisk': {output}"
        assert "22.10.1" in output, f"asterisk -V output missing '22.10.1': {output}"
        self.output.info("asterisk -V version verified (contains 'Asterisk' and '22.10.1')")
