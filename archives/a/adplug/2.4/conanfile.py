#!/usr/bin/env python3
"""Conan recipe for adplug 2.4 — AdPlug AdLib sound player library (Autotools)."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AdplugConan(ConanFile):
    name = "adplug"
    version = "2.4"
    description = "AdPlug - a free AdLib sound player library"
    license = "LGPL-2.1-or-later"
    homepage = "https://adplug.github.io/"
    url = "https://github.com/adplug/adplug"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libbinio/1.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # adplug configure 依赖 libbinio 的 pkg-config 元数据。
        # libbinio 包的 .pc 中 prefix=/ 导致路径错误（-I//include/libbinio），
        # 因此直接用 configure 支持的环境变量传递 include/lib 路径。
        # OHOS 环境无 makeinfo，make install 会在 doc/libadplug.info 目标失败。
        # 用 MAKEINFO=true 覆盖（true 命令忽略参数返回 0），跳过文档生成。
        tc.configure_args.append("MAKEINFO=true")
        env = tc.environment()
        libbinio_pkg = self.dependencies["libbinio"].package_folder
        # libbinio 头文件位于 include/libbinio/（binfile.h 等），源码用 #include <binfile.h>
        inc_dir = os.path.join(libbinio_pkg, "include", "libbinio")
        lib_dir = os.path.join(libbinio_pkg, "lib")
        env.define("libbinio_CFLAGS", f"-I{inc_dir}")
        # 链接需加 -lclang_rt.builtins：aarch64 上 long double 运算
        # 生成 __addtf3 等 quad-float 辅助符号，由 compiler-rt builtins 提供
        env.define("libbinio_LIBS", f"-L{lib_dir} -lbinio -lclang_rt.builtins")
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["adplug"]
        self.cpp_info.requires = ["libbinio::libbinio"]
