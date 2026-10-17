#!/usr/bin/env python3
"""Conan recipe for iowow 1.5.2 — the skiplist based persistent key/value storage engine.

iowow 使用 Autark 构建系统（顶层 build.sh 包装器），不是 autotools：
  ./build.sh --prefix=<prefix>  构建并安装（头文件 → include/iowow/，库 → lib/）。

配方要点：
- 官方源码 GitHub Softmotions/iowow tag v1.5.2（R39），CI 自动镜像 fallback；
- 默认静态库（R26 语义，包内 libiowow.a），不输出系统同名 .so；
- R33：编译器显式从 Conan conf（tools.build:compiler_executables）读取，
  不使用裸 ${CC} 等可能未定义的 shell 变量；
- 头文件安装于 include/iowow/，消费者 include <iowow/iowow.h> 等。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class IowowConan(ConanFile):
    name = "iowow"
    version = "1.5.2"
    description = "iowow — the skiplist based persistent key/value storage engine"
    license = "MIT"
    homepage = "https://github.com/Softmotions/iowow"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器从 Conan conf 读取，不依赖未定义的 shell 变量
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", os.environ.get("CC", "clang"))
        # 静态库默认（R26 语义）；shared 选项映射到 Autark 开关
        env = {
            "CC": cc,
            "BUILD_TYPE": "Release",
        }
        if self.options.shared:
            env["IOWOW_BUILD_SHARED_LIBS"] = "1"
        # build.sh 需要 `install` 工具（本机在 /bin）；确保在 PATH 内
        path = os.environ.get("PATH", "")
        if "/bin" not in path.split(":"):
            os.environ["PATH"] = "/bin:" + path
        env_str = " ".join(f'{k}="{v}"' for k, v in env.items())
        stage = os.path.join(self.build_folder, "stage")
        # Autark: build.sh → build + install；--prefix=stage 隔离安装目录
        self.run(f"{env_str} ./build.sh --prefix={stage} -J1",
                 cwd=self.source_folder)

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        copy(self, "*.h", src=os.path.join(stage, "include", "iowow"),
             dst=os.path.join(self.package_folder, "include", "iowow"))
        # autark 安装库文件到 lib64（64 位）或 lib（32 位），两处都兼容
        for libdir in ("lib64", "lib"):
            if os.path.isdir(os.path.join(stage, libdir)):
                copy(self, "libiowow.a", src=os.path.join(stage, libdir),
                     dst=os.path.join(self.package_folder, "lib"))
                if self.options.shared:
                    copy(self, "libiowow.so", src=os.path.join(stage, libdir),
                         dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libiowow.pc", src=os.path.join(stage, "lib", "pkgconfig"),
             dst=os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["iowow"]
        if self.options.shared:
            self.cpp_info.defines.append("IOWOW_SHARED")