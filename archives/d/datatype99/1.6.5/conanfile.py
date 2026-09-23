#!/usr/bin/env python3
"""Conan recipe for datatype99 1.6.5 (hirrolot/datatype99).

datatype99 是 C99 的代数数据类型（sum type）库：datatype()/derive() 宏在
预处理期生成 tagged union + 模式匹配宏，header-only（单头 datatype99.h），
依赖 metalang99（预处理元编程引擎，本仓已适配 1.13.5，与上游
CMakeLists.txt FetchContent 钉的版本一致）。

OHOS 适配要点：
- 上游 CMakeLists.txt 用 FetchContent 现场下载 metalang99 —— 沙箱禁用网络
  拉取且与 conan 依赖管理冲突 → 不走上游 CMake，requires metalang99/1.13.5
  （同版本），build() 内直接编译测试。
- 上游 tests/CMakeLists.txt 给 GCC/Clang 加 -fsanitize=address：OHOS musl
  clang 的 ASan 支持不在本配方保证范围内，直编译时省略（上游断言语义不变：
  tests.c 等为运行时 assert 自检，version.c 为编译期 ML99_ASSERT_UNEVAL）。
- 5 个测试程序全部直接编译实跑：tests(40 assert)/metalang99_compliant(5)/
  derive(4)/record_derive(1)/version(编译期断言，编译成功即通过)。
"""
from conan import ConanFile
from conan.tools.files import copy, get
import os


class Datatype99Conan(ConanFile):
    name = "datatype99"
    version = "1.6.5"
    description = "Algebraic data types for C99 (sum types + pattern matching macros)"
    license = "MIT"
    homepage = "https://github.com/hirrolot/datatype99"
    url = ""  # CI fills this
    topics = ("algebraic-data-types", "sum-types", "metaprogramming", "header-only")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def requirements(self):
        # 与上游 CMakeLists.txt FetchContent 钉的版本一致
        self.requires("metalang99/1.13.5", transitive_headers=True)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ml99 = self.dependencies["metalang99"].cpp_info
        incs = " ".join(["-I" + self.source_folder] + ["-I" + p for p in ml99.includedirs])
        tdir = os.path.join(self.source_folder, "tests")
        # 层1 上游官方测试：5 个测试程序全量编译实跑（不加 -fsanitize=address，
        # 断言语义不变）。version.c 是编译期 ML99_ASSERT_UNEVAL——编译成功即通过。
        # -std=c11：derive.c/record_derive.c 的 deriver 用 static_assert（C11 起），
        # 上游 CMake 不设标准走编译器默认（clang 默认 gnu17）；c99 下 static_assert
        # 未定义 → ML99_TERMS 里残留 static_assert(...) 记号 → "type specifier
        # missing" + "expected parameter declarator"（CI #44019 实测）。
        for name in ("tests", "metalang99_compliant", "derive", "record_derive", "version"):
            self.run(f"{cc} -std=c11 -O1 {incs} {os.path.join(tdir, name + '.c')} -o {name}")
            self.run(f"./{name}")

    def package(self):
        copy(self, "datatype99.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
