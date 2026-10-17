#!/usr/bin/env python3
"""Conan recipe for hidapi 0.12 (CMake)."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class HidapiConan(ConanFile):
    name = "hidapi"
    version = "0.12.1"
    description = "A simple library for communicating with USB and Bluetooth HID devices"
    license = "MIT"
    homepage = "https://github.com/libusb/hidapi"
    url = "https://github.com/libusb/hidapi"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libudev-zero/1.0.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # hidraw 后端通过 pkg_check_modules(libudev REQUIRED) 查找 libudev.pc。
        # libudev-zero 包内自带的 libudev.pc 的 prefix 指向已清理的 conan 构建
        # 目录（b/），导致 CMake 报 "PkgConfig::libudev includes non-existent
        # path"。因此这里生成一份 prefix 指向 package_folder 的修正版
        # libudev.pc，写入 generators/lib/pkgconfig/ 下——generators 目录已被
        # CMakeToolchain PREPEND 进 CMAKE_PREFIX_PATH，配合
        # PKG_CONFIG_USE_CMAKE_PREFIX_PATH=TRUE，FindPkgConfig 会优先搜到它。
        # 注意：必须用 self.dependencies["libudev-zero"]（__getitem__ 按名字访问），
        # 不能用 .get("libudev-zero")——conan 2.x 的 get() 接收完整 ref 而非包名。
        libudev = self.dependencies["libudev-zero"]
        pkg_dir = os.path.join(self.generators_folder, "lib", "pkgconfig")
        os.makedirs(pkg_dir, exist_ok=True)
        pc_content = (
            "prefix={prefix}\n"
            "exec_prefix=${{prefix}}\n"
            "libdir=${{exec_prefix}}/lib\n"
            "includedir=${{prefix}}/include\n"
            "\n"
            "Name: libudev\n"
            "Description: Daemonless replacement for libudev\n"
            "Version: 251\n"
            "Libs: -L${{libdir}} -ludev\n"
            "Cflags: -I${{includedir}}\n"
        ).format(prefix=libudev.package_folder)
        with open(os.path.join(pkg_dir, "libudev.pc"), "w", encoding="utf-8") as f:
            f.write(pc_content)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Add project-specific CMake variables here:
        # tc.variables["ENABLE_FOO"] = "ON"
        # CMAKE_POLICY_VERSION_MINIMUM must be a cache variable (-D) to
        # bypass cmake_minimum_required(VERSION 3.1.3) on CMake >= 3.5.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # PKG_CONFIG_USE_CMAKE_PREFIX_PATH: 让 CMake 的 FindPkgConfig 模块
        # 从 CMAKE_PREFIX_PATH（含 generators 目录，含我们生成的 libudev.pc）
        # 中搜索 .pc 文件
        tc.variables["PKG_CONFIG_USE_CMAKE_PREFIX_PATH"] = "TRUE"
        tc.variables["HIDAPI_NO_ICONV"] = "ON"
        tc.variables["HIDAPI_WITH_LIBUSB"] = "OFF"
        tc.variables["HIDAPI_WITH_HIDRAW"] = "ON"
        # E266: OHOS SDK lld depends on libxml2.so.16 which may not be
        # found by the dynamic linker. Use GNU ld instead.
        tc.extra_exelinkflags.append("-fuse-ld=/data/service/hnp/bin/ld")
        tc.extra_sharedlinkflags.append("-fuse-ld=/data/service/hnp/bin/ld")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # hidraw backend is the only one built (HIDAPI_WITH_LIBUSB=OFF),
        # so the installed library is libhidapi-hidraw.a
        self.cpp_info.libs = ["hidapi-hidraw"]
