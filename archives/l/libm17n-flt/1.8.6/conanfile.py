#!/usr/bin/env python3
"""Conan recipe for libm17n-flt 1.8.6 — m17n 字体布局表库（autotools）.

m17n-lib 1.8.6 同一 tarball 构建 libm17n-core 与 libm17n-flt，
本包以 libm17n-flt 命名，随包安装两个库（FLT 依赖 core）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libm17nFltConan(ConanFile):
    name = "libm17n-flt"
    version = "1.8.6"
    description = "m17n-lib Font Layout Table (FLT) — multilingual text shaping"
    license = "LGPL-2.1"
    homepage = "https://www.nongnu.org/m17n/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess 无法识别 HarmonyOS（UNAME_SYSTEM=HarmonyOS）
        # ——显式指定 build/host triplet（aarch64-unknown-linux-ohos）。
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        # 禁用可选重依赖（X11 GUI / OpenType / fontconfig / GD），
        # 避免 X11/OTF/freetype/fontconfig 依赖链，只保留 core+flt。
        # --disable-nls：跳过内置 gettext intl 子目录（lock.h 的
        # #pragma weak pthread_cancel 在 OHOS musl 无该符号致编译失败）。
        tc.configure_args.extend([
            "--disable-nls",
            "--disable-gui",
            "--without-libotf",
            "--without-fontconfig",
            "--without-gd",
        ])
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 符号归属实测（三库分散）：
        #   libm17n-flt.a  — m17n_init_flt/m17n_fini_flt（FLT 子系统）
        #   libm17n-core.a — Mcategory/Mtext 等核心数据符号
        #   libm17n.a      — m17n_init/m17n_fini/mconv_list_codings 等核心函数
        # 消费者需三者全链（顺序：flt → core → m17n）。
        self.cpp_info.libs = ["m17n-flt", "m17n-core", "m17n"]
        self.cpp_info.set_property("pkg_config_name", "m17n-flt")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
