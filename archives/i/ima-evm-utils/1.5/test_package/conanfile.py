#!/usr/bin/env python3
"""ima-evm-utils test_package — 消费者视角验证 libimaevm 可用性.

验证：imaevm.h 可包含 + -limaevm 链接 + evmctl --version 运行。
断言口径见 MANIFEST.yml。
"""
from conan import ConanFile
from conan.tools.build import can_run
import os


class ImaEvmUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            cc_map = self.conf.get("tools.build:compiler_executables", default={}) or {}
            cc = cc_map.get("c") or cc_map.get("cpp") or os.environ.get(
                "CC", str(self.settings.compiler))
            pkg = self.dependencies["ima-evm-utils"]
            op = self.dependencies["openssl"]

            src = os.path.join(self.source_folder, "src", "test_imaevm.c")
            bin_path = os.path.join(self.build_folder, "test_imaevm")

            pkg_inc = " ".join("-I" + os.path.join(pkg.package_folder, d)
                               for d in pkg.cpp_info.includedirs)
            pkg_lib = " ".join("-L" + os.path.join(pkg.package_folder, d)
                               for d in pkg.cpp_info.libdirs)
            op_inc = " ".join("-I" + os.path.join(op.package_folder, d)
                              for d in op.cpp_info.includedirs)
            op_lib = " ".join("-L" + os.path.join(op.package_folder, d)
                              for d in op.cpp_info.libdirs)
            self.run(
                f"{cc} -o {bin_path} {src} {pkg_inc} {op_inc} {pkg_lib} {op_lib} "
                f"-limaevm -lcrypto -lm",
                env="conanbuild")
            os.environ["EVMCTL"] = os.path.join(pkg.package_folder, "bin", "evmctl")
            self.run(bin_path, env="conanrun")
