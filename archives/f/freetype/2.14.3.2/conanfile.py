#!/usr/bin/env python3
"""Conan recipe — freetype 2.14.3.2 for HarmonyOS PC (aarch64).

Zero-external-dependency leaf build (R36 依赖先发布):
freetype 与 harfbuzz 存在编译期循环依赖，首版必须以无 hb 配置构建，
禁全部可选依赖（--with-zlib/no/bzip2/png/harfbuzz/brotli=no）。

OHOS 平台适配点（知识图谱 E007/E011）：
- E007: config.guess/config.sub 打补丁识别 HarmonyOS → aarch64-unknown-linux-ohos
  （取代旧版 uname-shim 内联 hack，patch 声明在 conandata.yml，R6 合规）
- E011: configure 临时目录改用 TMPDIR + umask 022（HMDFS 权限限制）
- R33: 编译器/工具从 Conan Toolchain 环境注入（freetype builds/unix/detect.mk
  默认探测用 cc 而非 clang → 注入 CC/CXX/LD/AR/...，CI #29062 教训）
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FreetypeConan(ConanFile):
    name = "freetype"
    version = "2.14.3.2"
    description = "Free, high-quality font rendering engine supporting TrueType, OpenType, CFF and others"
    license = "FreeType-License OR GPL-2.0"
    homepage = "https://freetype.org/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 零外部依赖：可选依赖全禁，harfbuzz 留待后续带 hb 版本
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 禁全部可选依赖 → 零外部依赖叶子节点（harfbuzz 与 freetype 循环）
        tc.configure_args.append("--with-zlib=no")
        tc.configure_args.append("--with-bzip2=no")
        tc.configure_args.append("--with-png=no")
        tc.configure_args.append("--with-harfbuzz=no")
        tc.configure_args.append("--with-brotli=no")
        if self.options.shared:
            # 非系统同名库默认动态（R26 仅约束系统同名库；/lib /lib64 无 libfreetype）
            tc.configure_args.append("--disable-static")
        # R33: 编译器/工具必须从 Conan Toolchain 环境获取，禁止裸用 shell ${CC}。
        # OHOS 上 freetype 的 builds/unix/detect.mk 自动检测用默认 cc 而非 clang
        # （CI #29062: "C compiler cannot create executables" Error 77），
        # 参照 libxext 先例注入编译器/工具环境变量。
        if str(self.settings.os) == "OHOS":
            env = tc.environment()
            shell = "/data/service/hnp/bin/bash"
            env.define_path("SHELL", shell)
            env.define_path("CONFIG_SHELL", shell)
            env.define_path("CC", "/data/service/hnp/bin/clang")
            env.define_path("CXX", "/data/service/hnp/bin/clang++")
            env.define_path("LD", "/data/service/hnp/bin/ld.lld")
            env.define_path("AR", "/data/service/hnp/bin/llvm-ar")
            env.define_path("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
            env.define_path("STRIP", "/data/service/hnp/bin/llvm-strip")
            env.define_path("NM", "/data/service/hnp/bin/llvm-nm")
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
        self.cpp_info.libs = ["freetype"]
        # freetype 头装在 include/freetype2/（ft2build.h + freetype/*.h），非标准 include/ 根。
        self.cpp_info.includedirs = ["include/freetype2", "include"]
        # freetype2.pc 的 Version 是 libtool 号（version_info=26:6:20 → 26.6.20），非 release 2.14.3。
        # fontconfig/cairo 按此判 `freetype2 >= 21.0.15`；conan 默认写 recipe 版本 2.14.3 会判假。
        self.cpp_info.set_property("system_package_version", "26.6.20")
        self.cpp_info.set_property("cmake_file_name", "freetype")
        self.cpp_info.set_property("cmake_target_name", "freetype::freetype")
        self.cpp_info.set_property("pkg_config_name", "freetype2")
