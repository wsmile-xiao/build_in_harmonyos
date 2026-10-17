#!/usr/bin/env python3
"""Conan recipe for libindi 2.2.2.1 — INDI astronomy device control framework.

History-based adaptation (archives/l/libindi/2.2.2, W0b):
  - E092: CMake 不识别 HarmonyOS 平台 → 强制 CMAKE_SYSTEM_NAME=Linux
  - libs/indibase/indigpsinterface.cpp: stime() syscall 不可用 → clock_settime()
  - libs/indicore/sharedblob.c: OHOS 不支持 mremap → munmap+mmap 兼容路径
  - libs/sockets/select.h: OHOS libc 不通过 sys/socket.h 传递 fd_set → 显式 include
  - CMakeLists: link_libraries(c++ c++abi)（OHOS libc++ 标准库）

Conan 侧适配（本次新增, 记录于 notes.md）:
  - conan CMakeToolchain 默认 CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, 会 shadow 掉
    libindi 自带 Find*.cmake 的旧式变量 (CFITSIO_INCLUDE_DIR 等) → 在 toolchain
    末尾强制 OFF, 使自定义 Find 模块生效
  - libs/dsp/fft.c 直接 include <fftw3.h>, 但 libindi 的 CMake 不注入 FFTW3
    include 路径 (系统构建靠 /usr/include) → 通过 extra_cflags 注入 conan fftw 头
  - INDI_BUILD_SHARED 必须保持 ON: examples/tests 直接引用共享目标名
    (indiclient/indidriver), 关闭后链接报 -lindiclient 找不到
"""
import os
import textwrap

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PreferConfigOffBlock(Block):
    """toolchain 末尾强制关闭 config 优先, 让 libindi 自带 Find*.cmake 模块生效"""
    template = textwrap.dedent("""\
        set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)
    """)


class LibindiConan(ConanFile):
    name = "libindi"
    version = "2.2.2.1"
    description = "INDI (Instrument Neutral Distributed Interface) astronomy device control protocol and library"
    license = "LGPL-2.1+"
    homepage = "https://indilib.org"
    url = "https://github.com/indilib/indi"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # 默认 shared=False（同时产出 .a 与 .so）：INDI_BUILD_SHARED 恒 ON 保证
    # examples/tests 的共享目标名存在；test_package 用静态 .a 链接，
    # 规避本机 host-musl 加载 OHOS 共享库的限制（argp-standalone 同款模式）
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("cfitsio/4.6.4")
        self.requires("libnova/0.16")
        self.requires("libusb/1.0.27")
        self.requires("curl/8.15.0.1")
        self.requires("gsl/2.8")
        self.requires("libjpeg/10")
        self.requires("zlib/1.3.1.1")
        self.requires("fftw/3.3.11")
        self.requires("libev/4.33")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake 不识别 HarmonyOS 平台，必须显式用 Linux
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["INDI_BUILD_QT_CLIENT"] = "OFF"
        tc.variables["INDI_BUILD_UNITTESTS"] = "OFF"
        # /lib/udev 是绝对安装路径，OHOS 上不可写，禁用 udev rules 安装
        tc.variables["INDI_INSTALL_UDEV_RULES"] = "OFF"
        # INDI_BUILD_SHARED 必须 ON：examples/tests 直接引用共享目标名
        # (indiclient/indidriver)，关闭后链接报 -lindiclient 找不到（历史验证同此）
        tc.variables["INDI_BUILD_SHARED"] = "ON"
        # shared=False 时同时产出静态库（R26 惯例）
        tc.variables["INDI_BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # libs/dsp/fft.c include <fftw3.h>，libindi CMake 不注入 FFTW3 头路径
        fftw_inc = self.dependencies["fftw"].cpp_info.includedirs[0]
        tc.extra_cflags.append(f'-I"{fftw_inc}"')
        tc.extra_cxxflags.append(f'-I"{fftw_inc}"')
        # 强制 libindi 自定义 Find*.cmake 生效（toolchain 末尾覆盖默认 ON）
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # R9 保守并行：内存受限机器默认 -j2，可用 tools.build:jobs 覆盖
        build_jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{build_jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["indiclient", "indidriver"]
        self.cpp_info.system_libs = ["m"]
        # OHOS libc++ 标准库（历史验证：需链接 c++/c++abi）
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self.cpp_info.system_libs.extend(["c++", "c++abi"])
        self.cpp_info.set_property("cmake_file_name", "libindi")
        self.cpp_info.set_property("cmake_target_name", "libindi::libindi")
