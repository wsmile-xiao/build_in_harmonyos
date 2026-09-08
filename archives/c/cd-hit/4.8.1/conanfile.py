#!/usr/bin/env python3
"""Conan recipe — cd-hit 4.8.1 (plain Makefile C++ tool, MIT).

CD-HIT 按序列相似度对蛋白质/核酸序列快速聚类（去冗余），
产物为 6 个命令行可执行程序（R38 tool 类型，需 commands.json）。
构建为纯 make（无 configure），Makefile 硬编码 CC=g++，
配方在命令行用 OHOS 工具链 clang++ 覆盖（R33：编译器来自工具链而非 shell 环境变量）。
zlib 为 .gz 输入支持（README 要求），由 Conan 依赖注入（R49）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CdhitConan(ConanFile):
    name = "cd-hit"
    version = "4.8.1"
    description = "CD-HIT clusters similar biological sequences (protein/DNA) at high identity"
    license = "MIT"
    homepage = "https://github.com/weizhongli/cdhit"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    requires = "zlib/1.3.1"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R49: 依赖注入指向 Conan 缓存的私有包目录（不碰共享 /usr/local）。
        # 用唯一脚本名（勿用保留聚合名 conanbuild，否则生成自引用 env 致 SIGSEGV）。
        # env 变量经 makefile 的 `CCFLAGS := $(CPPFLAGS)...` / `LDFLAGS += -lz -o` 自然累加。
        zlib_pkg = self.dependencies["zlib"].package_folder
        env = Environment()
        env.define("CPPFLAGS", f"-I{zlib_pkg}/include")
        env.define("LDFLAGS", f"-L{zlib_pkg}/lib")
        env.vars(self).save_script("cdhit_build_env")

    def build(self):
        apply_conandata_patches(self)
        # Makefile 硬编码 CC=g++，命令行覆盖为 OHOS clang 工具链；
        # 默认 -fopenmp + -DWITH_ZLIB（与上游默认一致，本地已验证 clang++ 可编译链接）
        self.run(
            "make CC=clang++ CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib -j2",
            env="cdhit_build_env",
            cwd=self.source_folder,
        )

    def package(self):
        for prog in ("cd-hit", "cd-hit-est", "cd-hit-2d",
                     "cd-hit-est-2d", "cd-hit-div", "cd-hit-454"):
            copy(self, prog, self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []  # tool 包：仅可执行程序（R38 commands.json 声明）
        self.cpp_info.bindirs = ["bin"]
