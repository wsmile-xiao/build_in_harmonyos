#!/usr/bin/env python3
"""Conan recipe — mda-lv2 1.2.12 (MDA LV2 plugin collection).

meson 构建，36 个 LV2 插件模块（.so）+ 46 个 TTL 数据文件安装为单一
bundle：lib/lv2/mda.lv2/。无源码补丁（上游 meson.build 直接兼容 OHOS）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class MdaLv2Conan(ConanFile):
    name = "mda-lv2"
    version = "1.2.12"
    description = "MDA LV2 plugins (ported MDA audio effects, mda.lv2)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/drobilla/mda-lv2"
    url = "https://gitlab.com/drobilla/mda-lv2"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # library 类型必须声明 shared 选项（conan 2 校验）——LV2 插件本质是
    # 可加载共享模块（dlopen），shared=True 是唯一有意义的取值
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    # 无补丁（保留目录声明以对齐 sherlock.lv2 先例结构）
    exports_sources = "patches/*"

    def requirements(self):
        # 上游 meson.build: dependency('lv2', version: '>= 1.16.0',
        # include_type: 'system')。mda-lv2 全部 36 个插件模块仅依赖 lv2
        # 头文件（lv2/lv2plug.in/ns/lv2core/lv2.h），无其他库依赖
        self.requires("lv2/1.18.11-git")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # lv2 依赖经 pkg-config 发现（sherlock.lv2 同款）：PkgConfigDeps 生成
        # .pc 到 generators 目录，meson 才能找到 "Run-time dependency lv2"
        pcd = PkgConfigDeps(self)
        pcd.generate()
        tc = MesonToolchain(self)
        # meson 安装布局：prefix/lib/lv2/mda.lv2/（36 .so + 37 .ttl 含
        # manifest.ttl + 9 presets）。上游 meson_options.txt: lv2dir 为空时
        # 取 prefix/libdir/lv2——直接置相对路径 lib/lv2 与 sherlock 先例一致
        tc.project_options["lv2dir"] = "lib/lv2"
        # 原生构建（本机即 OHOS arm64）：不设 sys_root——设置后会拼坏
        # pkg-config -isystem 路径（exploration 期已验证；sherlock 同例）
        tc.generate()
        # OHOS 沙箱 subprocess 裸命令查找失败（sord 先例注入 ar 绝对路径）：
        # native file 注入 clang/clang++/ar 绝对路径
        clang_path = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clangpp_path = shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        ar_path = shutil.which("ar") or "/data/service/hnp/bin/ar"
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with open(native_file) as f:
            content = f.read()
        content = content.replace(
            "c = 'clang'",
            f"c = '{clang_path}'"
        ).replace(
            "cpp = 'clang++'",
            f"cpp = '{clangpp_path}'"
        )
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nc ="
        )
        with open(native_file, "w") as f:
            f.write(content)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # 上游以 LICENSES/ 目录分发（GPL-2.0-or-later.txt 为插件主体，
        # 0BSD/MIT 为 lvz wrapper 构建脚本）
        copy(self, "*.txt", src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # LV2 插件 bundle 无 headers/libs（宿主 dlopen 加载）：includedirs/
        # libdirs 置空（sherlock.lv2 先例）。libdirs 置空避免 conan 在
        # VirtualRunEnv 中为不存在的 lib 目录生成 LD_LIBRARY_PATH 条目
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
