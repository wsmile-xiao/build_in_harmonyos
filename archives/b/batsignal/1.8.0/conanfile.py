#!/usr/bin/env python3
"""Conan recipe for batsignal 1.8.0 — lightweight battery daemon (C, .POSIX make).

batsignal 是轻量电池守护进程（C 语言，.POSIX 标准 make 构建）——监听
/sys/class/power_supply 电池状态，低电量/充满时用 libnotify 发桌面通知。
依赖：libnotify（pkg-config --cflags/--libs libnotify——build_in_harmonyos
已适配 libnotify/0.8.3，制品仓已发布）+ libm（系统自带）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class BatsignalConan(ConanFile):
    name = "batsignal"
    version = "1.8.0"
    description = "Lightweight battery daemon for notifying when battery status changes"
    license = "ISC"
    homepage = "https://github.com/electrickite/batsignal"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # libnotify（桌面通知库——pkg-config libnotify）——制品仓已发布；
        # libm 系统自带
        self.requires("libnotify/0.8.3")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("batsignal is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL 无 .tar.gz 扩展名——conan get() 按扩展名误判 zip
        # （BadZipFile）——显式 filename= 指定（bash-git-prompt/alot 同款教训）
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="batsignal-1.8.0.tar.gz")

    def generate(self):
        # PkgConfigDeps 生成 libnotify.pc——Makefile 用 pkg-config --cflags/--libs
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        # .POSIX make：make 生成 batsignal + batsignal.1（main.h 中 VERSION/
        # PROGNAME 用 sed 替换）——-j1 绕 OHOS 沙箱禁 mkfifo（make jobserver）；
        # Makefile 在 source_folder（basic_layout 下 build_folder 无源码）——
        # cwd 指 source_folder 执行
        # OHOS 无 cc（Makefile 默认 CC=cc）——命令内联 CC=clang；PkgConfigDeps
        # 生成的 libnotify.pc 在 generators_folder——PKG_CONFIG_PATH 指向它。
        # 注意：conan run() 的 env 参数是 list（非 dict）——环境变量内联进命令
        # Makefile 硬编码 CFLAGS_EXTRA 含 -Werror——clang C2x 下无原型函数
        # 声明报 -Wstrict-prototypes（aegean 同款）——命令行覆盖 CFLAGS_EXTRA
        # 追加 -Wno-error=strict-prototypes（GNU make 命令行变量优先）
        cmd = ("export CC=clang PKG_CONFIG_PATH=\"%s:$PKG_CONFIG_PATH\"; "
               "make -j1 CFLAGS_EXTRA=\"-pedantic -Wall -Wextra -Werror "
               "-Wno-unused-parameter -Os -Wno-error=strict-prototypes\""
               % self.generators_folder)
        self.run(cmd, cwd=self.source_folder, env="conanrun")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "batsignal", src=self.source_folder, dst=bin_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
