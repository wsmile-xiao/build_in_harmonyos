#!/usr/bin/env python3
"""Conan recipe for kinect-audio-setup 0.5 on HarmonyOS PC.

kinect-audio-setup 使 Microsoft Kinect 感应器的音频输入在 GNU/Linux 上可用：
在设备首次插入时上传固件（kinect_upload_fw），并配置 udev 规则自动触发。
本配方构建 core 的 C 工具 kinect_upload_fw（顶层 Makefile 递归调用
kinect_upload_fw/Makefile），依赖 libusb-1.0（通过 pkg-config 发现）。

产物：sbin/kinect_upload_fw（命令行工具，静态链接 libusb-1.0.a，仅动态
依赖 libc.so）。纯 Makefile 构建系统（无 configure），R9 使用 -j1。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class KinectAudioSetupConan(ConanFile):
    name = "kinect-audio-setup"
    version = "0.5"
    description = "Tools to enable audio input from the Microsoft Kinect sensor device"
    license = "BSD-2-Clause"
    homepage = "https://git.ao2.it/kinect-audio-setup.git"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("kinect", "usb", "audio", "firmware", "udev")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # libusb 配方默认 shared=True；构建期工具 endian 会动态链接
        # libusb-1.0.so.0 并在 make 内运行（找不到 .so 报
        # "Error loading shared library libusb-1.0.so.0"）。
        # 强制 shared=False（静态 .a）：endian/kinect_upload_fw 均静态链入
        # libusb，产物仅依赖 libc.so（R26 语义，探索编译已验证）。
        self.requires("libusb/1.0.27", options={"shared": False})

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # kinect_upload_fw/Makefile 通过 pkg-config 发现 libusb-1.0：
        #   CFLAGS  += $(shell pkg-config --cflags libusb-1.0)
        #   LDLIBS  += $(shell pkg-config --libs libusb-1.0)
        # PkgConfigDeps 生成 conan 化 .pc（正确的 prefix=包目录）。
        # 但裸 Makefile（无 autotools toolchain）不会自动把 generators 目录
        # 加入 PKG_CONFIG_PATH，须手动注入（R49 私有 prefix 语义）。
        PkgConfigDeps(self).generate()
        env = Environment()
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self).save_script("kinect_pkgconfig")

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器从 conan conf 获取（不用 ${CC} 等 shell 变量）
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: 始终 -j1
        self.run("make CC={} -j1".format(cc), env="conanbuild")
        # 上游无 make check 目标（Makefile 仅 all/install/install_udev_rules/clean），
        # 见 notes.md 上游测试申报表；R51 实测说明见 test_package/ 与 notes.md。

    def package(self):
        # 顶层 Makefile 的 install 目标使用系统 install 命令（OHOS 无 GNU
        # install），且会安装 udev 规则到 /lib/udev —— 不属于可移植包内容，
        # 故直接拷贝编译产物（保持 PREFIX=sbin 语义，与上游默认一致）。
        copy(self, "kinect_upload_fw",
             src=os.path.join(self.source_folder, "kinect_upload_fw"),
             dst=os.path.join(self.package_folder, "sbin"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "sbin"))