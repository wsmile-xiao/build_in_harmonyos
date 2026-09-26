#!/usr/bin/env python3
"""Conan recipe for iwnet 1.3.1 — Pure C async HTTP/IO framework.

构建系统：Autark（build.sh 包装的 Makefile 驱动），非 Autotools/CMake。
- 上游 build.sh 在构建期通过 iowow.autark 从官方 GitHub 拉取并编译 iowow
  （iwnet 的强依赖，ohpcd 制品仓尚未发布 iowow/1.5.x，故自包含构建）。
- 构建产物按 --prefix 安装到 lib64/、include/、lib/pkgconfig/。
- 测试链接 cunit（仅 IWNET_RUN_TESTS=1 时），W3/conan create 默认不启用测试，
  测试运行由 CI 侧 test_package/ 与独立测试流程覆盖。
- 本配方不注入共享系统前缀（R49）：仅使用 Conan 管理的 prefix。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class IwnetConan(ConanFile):
    name = "iwnet"
    version = "1.3.1"
    description = "Pure C Asynchronous HTTP/IO framework with routing, websockets, SSL and reverse proxy"
    license = "MIT"
    homepage = "https://github.com/Softmotions/iwnet"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Autark 为 in-source 构建（autark-cache 生成在源码目录），
        # 使用标准 layout 但实际在 source_folder 内执行 build.sh。
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: 编译器从 Conan conf 获取，不依赖 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or compilers.get("cpp") or "clang"
        self.output.info(f"using CC={cc}")

    def build(self):
        apply_conandata_patches(self)
        build_dir = self.source_folder
        # AUTARK_HOME 必须为绝对路径：相对路径在嵌套 iowow 构建时导致
        # execve 解析失败（本设备实测），此处强制绝对路径并创建目录。
        autark_home = os.path.join(build_dir, "autark-cache", ".autark-dist")
        os.makedirs(autark_home, exist_ok=True)
        # 静态构建（R26 同类默认静态；本库为非系统同名库，静态避免链接面问题）。
        # 环境变量以内联 VAR=value 前缀注入（兼容 Conan 2.x 多版本差异），
        # build.sh 为 sh 脚本，内联环境可被子进程（嵌套 autark/iowow）继承。
        self.output.info(f"Building iwnet with build.sh in {build_dir}")
        self.run(f"BUILD_TYPE=Release AUTARK_HOME={autark_home} ./build.sh --prefix={build_dir}",
                 cwd=build_dir)

    def package(self):
        src = self.source_folder
        # lib64/ 静态库
        copy(self, "*.a", src=os.path.join(src, "lib64"), dst=os.path.join(self.package_folder, "lib64"))
        # lib/ pkg-config 文件
        copy(self, "*.pc", src=os.path.join(src, "lib", "pkgconfig"),
             dst=os.path.join(self.package_folder, "lib", "pkgconfig"))
        # include/iwnet + include/iowow（iowow 为构建期自包含拉取，随包发布）
        copy(self, "*.h", src=os.path.join(src, "include", "iwnet"),
             dst=os.path.join(self.package_folder, "include", "iwnet"))
        copy(self, "*.h", src=os.path.join(src, "include", "iowow"),
             dst=os.path.join(self.package_folder, "include", "iowow"))

    def package_info(self):
        self.cpp_info.libdirs = ["lib64", "lib"]
        self.cpp_info.libs = ["iwnet", "iowow"]
        self.cpp_info.system_libs = ["pthread", "dl", "m"]
        self.cpp_info.defines = ["IW_STATIC"]