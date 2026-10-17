#!/usr/bin/env python3
"""Conan recipe for picotool 2.2.0 — Raspberry Pi Pico tool (C++).

picotool 是 Raspberry Pi Pico 的 elf2uf2/信息/擦除工具（C++，CMake 构建，
BSD-3-Clause）。依赖 libusb（制品仓有）+ pico-sdk（制品仓无——构建必需
PICO_SDK_PATH，从上游获取替代依赖）。

OHOS 适配:
- CMake 构建（路径 A）；
- pico-sdk 从上游获取（PICO_SDK_PATH 指向解压目录）；
- 测试: test_package 校验 picotool 可执行为有效 ELF（同 audispd 先例）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get


class PicotoolConan(ConanFile):
    name = "picotool"
    version = "2.2.0"
    description = "Raspberry Pi Pico tool (elf2uf2 / info / erase)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/raspberrypi/picotool"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def layout(self):
        # conan 2.x 默认 in-source——CMake 需 out-of-source（同 libsoup）
        self.folders.source = "."
        self.folders.build = "build"

    def requirements(self):
        self.requires("libusb/1.0.27")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        # CMake 编译器测试 = clang 调 SDK lld 链接测试程序，SDK lld 的
        # DT_NEEDED 含 libxml2.so.16（llvm/lib/ 下）——CI worker 上
        # LLVM lib 不在 loader 默认搜索路径 → lld 运行失败 → "C compiler
        # broken"（libseccomp 26072ddeb / picotool 先例）。build() 里
        # os.environ 注入会被 conanbuild 环境覆盖（libsoup 教训），必须
        # 用 buildenv_info.prepend 进 conanbuild.sh；推导用 Python
        # os.path.realpath（不依赖外部 realpath 命令，CI worker 原始
        # PATH 无其所在目录）。
        _llvm_lib = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.realpath("/data/service/hnp/bin/clang"))),
            "lib")
        if os.path.isdir(_llvm_lib):
            self.buildenv_info.prepend("LD_LIBRARY_PATH", _llvm_lib)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 下载 pico-sdk（PICO_SDK_PATH 构建必需——替代依赖）
        get(self, **self.conan_data["pico_sdk"], strip_root=True,
            destination="pico-sdk")

    def build(self):
        # LD_LIBRARY_PATH 已由 generate() 的 buildenv_info 注入 conanbuild
        # 环境（cmake.configure() 加载时生效）。此处 os.environ 兜底注入
        # 用纯 Python os.path.realpath（不依赖外部 realpath 命令）。
        _llvm_lib = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.realpath("/data/service/hnp/bin/clang"))),
            "lib")
        if os.path.isdir(_llvm_lib):
            _old_ld = os.environ.get("LD_LIBRARY_PATH", "")
            if _llvm_lib not in _old_ld:
                os.environ["LD_LIBRARY_PATH"] = (
                    _llvm_lib + (os.pathsep + _old_ld if _old_ld else ""))
            self.output.info(f"prepended {_llvm_lib} to LD_LIBRARY_PATH")
        # PICO_SDK_PATH 指向 pico-sdk 解压目录（CMake add_subdirectory
        # 其 boot_bootrom_headers/pico_platform）
        sdk_path = os.path.join(self.source_folder, "pico-sdk")
        if os.path.isdir(sdk_path):
            os.environ["PICO_SDK_PATH"] = sdk_path
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.conf_info.define("user.picotool:path", os.path.join(
            self.package_folder, "bin", "picotool"))
