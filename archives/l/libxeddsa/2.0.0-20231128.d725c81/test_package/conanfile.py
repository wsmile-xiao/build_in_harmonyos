#!/usr/bin/env python3
"""Conan test_package — libxeddsa 2.0.0-20231128.d725c81.

Direct-cc consumer (no CMake): compiles src/test_xeddsa.c against the
installed package (include/ + lib/libxeddsa.a) and runs it. Avoids the
OHOS-adapted CMakeToolchain CMAKE_SYSTEM_NAME=HarmonyOS mapping that
breaks `cmake.configure()` under vanilla CMake (archives/l/libsodium
1.0.20 + libmacaroons 0.3.0 precedent).

libsodium/1.0.22 is declared explicitly because the static libxeddsa.a
references sodium symbols (sodium_init, crypto_hash_sha512_*,
sodium_stackzero, ...); the consumer link closes the static chain with
the same ohpcd libsodium package.

The test is fully deterministic (fixed keys/nonces): RFC 8032 §7.1
Ed25519 vectors (empty message + 0x72 message), RFC 7748 §5.2 X25519
vectors and §6.1 Diffie-Hellman exchange, plus sign/verify and
conversion roundtrips with fixed inputs — no randombytes dependency.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class LibxeddsaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        # conan 2 test_package 需声明被测包（CI #23956 教训：
        # self.tested_reference_str）
        self.requires(self.tested_reference_str)
        # 静态闭包：libxeddsa.a 的 sodium 符号由 ohpcd libsodium 提供
        self.requires("libsodium/1.0.22")

    def layout(self):
        basic_layout(self)

    def test(self):
        # 编译命令用 conanbuild 环境（profile buildenv）的 ${CC} ${CFLAGS}
        # ——自带 --sysroot 与 --code-sign；裸调 conf 里的 clang-15 会缺
        # sysroot（stdio.h not found 实测）。libsodium/1.0.22 test_package
        # 同款写法。
        xed = self.dependencies["libxeddsa"]
        so = self.dependencies["libsodium"]
        xed_inc = os.path.join(xed.package_folder, "include")
        xed_lib = os.path.join(xed.package_folder, "lib", "libxeddsa.a")
        so_lib = os.path.join(so.package_folder, "lib", "libsodium.a")
        for path in (xed_lib, so_lib):
            if not os.path.isfile(path):
                raise FileNotFoundError(f"required static lib missing: {path}")
        src = os.path.join(self.source_folder, "src", "test_xeddsa.c")
        test_bin = os.path.join(self.build_folder, "test_xeddsa")
        self.run(
            f'"${{CC:-clang}}" -O2 -std=c99 ${{CFLAGS}} -o "{test_bin}" "{src}" '
            f'-I"{xed_inc}" "{xed_lib}" "{so_lib}"',
            env="conanbuild",
        )
        self.run(f'"{test_bin}"', env="conanrun")
