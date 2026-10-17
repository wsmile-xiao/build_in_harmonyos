#!/usr/bin/env python3
"""pigeonhole test_package — 消费者视角验证 libdovecot-sieve 可用性.

验证 libdovecot-sieve.a 可链接 + Sieve 核心 API（sieve_common 版本/初始化路径）。
断言口径见 MANIFEST.yml。
"""
from conan import ConanFile
from conan.tools.build import can_run
import os


class PigeonholeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            import os
            cc_map = self.conf.get("tools.build:compiler_executables", default={}) or {}
            # 测试源为 C（test_pigeonhole.c），必须优先取 C 编译器（clang），
            # 否则 clang++ 按 C++ 编译 .c → sieve-common.h 的 enum 前置引用
            # 报 "ISO C++ forbids forward references to 'enum' types"（CI #59648）
            cc = cc_map.get("c") or cc_map.get("cpp") or os.environ.get(
                "CC", str(self.settings.compiler))
            ph = self.dependencies["pigeonhole"]
            dv = self.dependencies["dovecot"]
            op = self.dependencies["openssl"]
            zl = self.dependencies["zlib"]

            src = os.path.join(self.source_folder, "src", "test_pigeonhole.c")
            bin_path = os.path.join(self.build_folder, "test_pigeonhole")

            ph_inc = " ".join(
                "-I" + os.path.join(ph.package_folder, d)
                for d in ph.cpp_info.includedirs)
            ph_lib = " ".join(
                "-L" + os.path.join(ph.package_folder, d)
                for d in ph.cpp_info.libdirs)
            dv_inc = " ".join(
                "-I" + os.path.join(dv.package_folder, d)
                for d in dv.cpp_info.includedirs)
            # pigeonhole 的 sieve 公共头实际安装到 pigeonhole 包
            # include/dovecot-pigeonhole/sieve/（CI 打包日志确认：
            # mkdir -p .../p//include/dovecot-pigeonhole/sieve +
            # install sieve-common.h 等），需追加
            # -I{pigeonhole_pkg}/include/dovecot-pigeonhole 才能
            # #include <sieve/sieve-common.h>（上轮加 dovecot include/dovecot
            # 路径错误，sieve 头不在 dovecot 包）。
            ph_inc += " -I" + os.path.join(ph.package_folder, "include", "dovecot-pigeonhole")
            # sieve-common.h 内部 #include "lib.h" 等依赖 dovecot 公共头
            # （dovecot 包 include/dovecot/ 下），需一并加
            # -I{dovecot_pkg}/include/dovecot（CI #51127：lib.h not found）
            dv_inc += " -I" + os.path.join(dv.package_folder, "include", "dovecot")
            dv_lib = " ".join(
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
            # pigeonhole/dovecot 公共头依赖构建期 config.h（已安装），需
            # -DHAVE_CONFIG_H 使其生效（两配方 package_info 均已声明该 define）
            # 链接顺序按依赖排列：libdovecot-sieve → libdovecot-storage →
            # libdovecot（mail_get_* 等符号在 libdovecot-storage，CI #63654
            # undefined symbol 根因），再补 openssl/zlib 传递依赖。
            self.run(
                f"{cc} -DHAVE_CONFIG_H -o {bin_path} {src} "
                f"{ph_inc} {dv_inc} {op_inc} {ph_lib} {dv_lib} {op_lib} {zl_lib} "
                f"-ldovecot-sieve -ldovecot-storage -ldovecot "
                f"-lssl -lcrypto -lz -lm -lpthread -ldl",
                env="conanbuild")
            self.run(bin_path, env="conanrun")
