#!/usr/bin/env python3
"""Conan test_package — librhash 1.4.4 L1 smoke test.

Two complementary tests run against the packaged artifacts:
  1. test.c   — direct librhash C API test (rhash_msg / rhash_init / rhash_update /
                rhash_final / rhash_print / rhash_get_digest_size / rhash_count …)
  2. test_rhash_cli.sh — CLI smoke test against the packaged `rhash` binary
                (assertions ported from upstream tests/test_rhash.sh).
"""
import os
from conan import ConanFile
from conan.errors import ConanException


class LibrhashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["librhash"]
        rhash_bin = os.path.join(dep.package_folder, "bin", "rhash")
        if not os.path.isfile(rhash_bin):
            raise ConanException(f"rhash CLI not packaged at {rhash_bin}")

        # 统一用 bash 执行：OHOS 上 /system/bin/sh (mksh) 无法运行 ELF，
        # 且默认 sh 可能是 dash（不支持 pipefail），因此一律走 CONFIG_SHELL/bash。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash" if self.settings.os == "OHOS" else "bash")

        # 1) 库 API 直接测试：编译 test.c 链接 librhash，覆盖核心 C API
        #    （CLI 测试之外的直接覆盖，避免库 API 回归只能靠 CLI 间接发现）。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        incdir = os.path.join(dep.package_folder, "include")
        libdir = os.path.join(dep.package_folder, "lib")
        test_c = os.path.join(self.recipe_folder, "test.c")
        # -Wl,-rpath 指向打包 lib 目录，保证运行时能定位共享库
        self.run(f"{cc} {test_c} -I{incdir} -L{libdir} -lrhash -Wl,-rpath,{libdir} -o test_api", env="conanrun")
        self.run(f"{bash} -c './test_api'", env="conanrun")

        # 2) CLI 冒烟测试（与库 API 测试并存，覆盖命令行路径）
        script = os.path.join(self.recipe_folder, "test_rhash_cli.sh")
        self.run(f"{bash} {script} {rhash_bin}", env="conanrun")
