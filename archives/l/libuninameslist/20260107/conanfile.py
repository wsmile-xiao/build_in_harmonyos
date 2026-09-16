#!/usr/bin/env python3
"""Conan recipe — libuninameslist 20260107 (Autotools, Unicode NamesList 数据查询库)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibuninameslistConan(ConanFile):
    name = "libuninameslist"
    version = "20260107"
    description = "Unicode NamesList 库，提供 Unicode 字符名称与注解查询 API"
    license = "MIT"
    homepage = "https://github.com/fontforge/libuninameslist"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 仓库惯例（cliquer 1.23 等已合入配方）：显式 musl 三元组，
        # 老 config.guess 不识别 HarmonyOS 主机，toolchain 对 OHOS 不注入三元组
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        # R26: 默认静态（本包非系统同名库，静态为安全缺省）
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["uninameslist"]
