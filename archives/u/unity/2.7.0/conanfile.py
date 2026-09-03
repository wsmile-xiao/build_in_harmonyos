#!/usr/bin/env python3
"""Conan recipe — Unity 2.7.0 (ThrowTheSwitch, ANSI C99)

Unity 核心 = src/unity.c + src/unity.h + src/unity_internals.h，100% ANSI C99，
无第三方依赖，纯用户态（无 POSIX 系统调用），可在 OHOS 上原生编译为共享库。
上游官方测试（test/Makefile `make test`）：8 个自检可执行文件
（arrays/core/doubles/floats/integers/integers_64/memory/strings），
runner 由上游自带 awk 脚本生成，CI worker 与本机均有 awk。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UnityConan(ConanFile):
    name = "unity"
    version = "2.7.0"
    description = "Unity - A Unit Test Framework for C (ThrowTheSwitch)"
    license = "MIT"
    homepage = "https://github.com/ThrowTheSwitch/Unity"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # L1: 上游官方测试套件（test/Makefile `make test`，8 个自检二进制，
        # runner 由上游自带 awk 脚本生成；无 ruby 依赖）
        self.run("make -C test CC=clang CFLAGS='-O2' test", cwd=self.source_folder)
        # 被测库本体：src/unity.c 编译为共享库。
        # 宏开关是编译期特性：库按最大能力（int64 + double）编译，
        # 与上游 test/Makefile 自检同款标志；未开启对应宏的消费者
        # 不会引用这些符号，互不影响。
        self.run("clang -std=c99 -O2 -fPIC -shared src/unity.c "
                 "-D UNITY_SUPPORT_64 -D UNITY_INCLUDE_DOUBLE -o libunity.so",
                 cwd=self.source_folder)

    def package(self):
        copy(self, "unity.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))
        copy(self, "unity_internals.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))
        copy(self, "libunity.so", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", os.path.join(self.source_folder, "extras"),
             os.path.join(self.package_folder, "include/extra"))
        copy(self, "LICENSE.txt", self.source_folder, self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["unity"]
