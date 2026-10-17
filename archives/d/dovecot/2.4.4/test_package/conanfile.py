#!/usr/bin/env python3
"""dovecot test_package — 消费者视角验证 libdovecot 核心 API.

验证 base64/buffer/pool 链路（base64.c/buffer.c/mempool.c，
即 OHOS 适配触及的核心 C 路径）：encode/decode roundtrip + 边界用例，
断言口径见 MANIFEST.yml。
"""
from conan import ConanFile
from conan.tools.build import can_run
import os


class DovecotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            import os
            cc_map = self.conf.get("tools.build:compiler_executables", default={}) or {}
            # test_dovecot.c 是 C 源码，dovecot base64.h 的 static inline 函数
            # 传 0 给 enum 参数（C 允许 int→enum 隐式转换，C++ 禁止，CI
            # #45138 报 no matching function）——必须用 C 编译器而非 C++。
            cc = cc_map.get("c") or cc_map.get("cpp") or os.environ.get(
                "CC", str(self.settings.compiler))
            dv = self.dependencies["dovecot"]
            op = self.dependencies["openssl"]
            zl = self.dependencies["zlib"]

            src = os.path.join(self.source_folder, "src", "test_dovecot.c")
            bin_path = os.path.join(self.build_folder, "test_dovecot")

            inc_flags = " ".join(
                "-I" + os.path.join(dv.package_folder, d)
                for d in dv.cpp_info.includedirs)
            lib_flags = " ".join(
                "-L" + os.path.join(dv.package_folder, d)
                for d in dv.cpp_info.libdirs)
            op_inc = " ".join(
                "-I" + os.path.join(op.package_folder, d)
                for d in op.cpp_info.includedirs)
            op_lib = " ".join(
                "-L" + os.path.join(op.package_folder, d)
                for d in op.cpp_info.libdirs)
            zl_lib = " ".join(
                "-L" + os.path.join(zl.package_folder, d)
                for d in zl.cpp_info.libdirs)
            # dovecot 公共头依赖构建期 config.h（已安装至 include/dovecot/），
            # 需 -DHAVE_CONFIG_H 使其生效（conanfile package_info 已声明该 define）
            self.run(
                f"{cc} -DHAVE_CONFIG_H -o {bin_path} {src} "
                f"{inc_flags} {op_inc} {lib_flags} {op_lib} {zl_lib} "
                f"-ldovecot -lssl -lcrypto -lz -lm -lpthread -ldl",
                env="conanbuild")
            self.run(bin_path, env="conanrun")
