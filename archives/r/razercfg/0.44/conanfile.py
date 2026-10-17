#!/usr/bin/env python3
"""Conan recipe for razercfg 0.44 — Razer device configuration tool.

razercfg 是 Razer 外设配置工具（C 库 librazer + 守护进程 razerd + Python 前端）。
CMake 构建。核心依赖 libusb-1.0（制品仓 libusb/1.0.27 已发布）。

适配要点：
- 上游根 CMakeLists 直接 `target_link_libraries(razer usb-1.0)`（裸库名），
  且 cmake.global 用 `find_path(libusb.h PATHS /usr/include/...)` 硬编码搜索
  → 通过 CMakeToolchain cache_variables 注入 CMAKE_INCLUDE_PATH /
  CMAKE_LIBRARY_PATH + 链接 flags（R49 私有 prefix，不触碰系统路径）。
- 上游 CMake 不安装 librazer 头文件 → package() 手动复制公共头。
- 补丁 0001：系统级安装（udev.rules / pm-hook / systemd）用 RAZERCFG_PKG_BUILD 保护。
- 补丁 0002：librazer.so 注入 SONAME（CMake 4 不识别 HarmonyOS 平台，
  VERSION/SOVERSION 链接命名机制未应用，需 LINK_FLAGS 显式 -soname）。
- 补丁 0003：razerd 链接时注入 RUNPATH=$ORIGIN/../lib（NEEDED 修正为 SONAME
  后运行时定位 librazer.so）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class RazercfgConan(ConanFile):
    name = "razercfg"
    version = "0.44"
    description = "Razer device configuration tool"
    license = "GPL-2.0-or-later"
    homepage = "https://bues.ch/h/razercfg"
    url = "https://bues.ch/releases/razercfg/"

    # 库+工具混合包：公开 librazer.so（E221 要求 library 建模以便 CMakeDeps
    # 导出 cpp_info.libs）；同时构建 razerd/razercfg CLI 工具，由软件级
    # commands.json（type=tool）声明，与 package_type 语义不冲突。
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游用裸库名 usb-1.0 + find_path(libusb.h)，注入 libusb 私有 prefix
        libusb = self.dependencies["libusb"]
        libusb_root = libusb.package_folder
        libusb_inc = os.path.join(libusb_root, "include", "libusb-1.0")
        libusb_lib = os.path.join(libusb_root, "lib")
        tc.cache_variables["CMAKE_INCLUDE_PATH"] = libusb_inc
        tc.cache_variables["CMAKE_LIBRARY_PATH"] = libusb_lib
        tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = "-L{}".format(libusb_lib)
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-L{}".format(libusb_lib)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # 跳过系统级 install_exec_cmd（ldconfig/systemctl/udevadm）
        os.environ["RAZERCFG_PKG_BUILD"] = "1"
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        os.environ["RAZERCFG_PKG_BUILD"] = "1"
        cmake = CMake(self)
        cmake.install()
        # 上游 CMake 不安装 librazer 公共头，手动复制（razer_private.h 为内部私有头不对外）
        copy(self, "librazer.h", src=os.path.join(self.source_folder, "librazer"),
             dst=os.path.join(self.package_folder, "include", "librazer"))

    def package_info(self):
        self.cpp_info.libs = ["razer"]
        self.cpp_info.includedirs = ["include"]
        # razercfg 产出 razerd 守护进程可执行文件（bin/），声明 bindirs
        # 以匹配 R38（CLI 包须有软件级 commands.json），
        # 避免 preflight PF8 误判为纯库包。
        self.cpp_info.bindirs = ["bin"]
