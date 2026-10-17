#!/usr/bin/env python3
"""Conan recipe — asmotor 1.0.0

ASMotor: portable and generic assembler engine and development system
written in ANSI C (C99). Package consists of the assembler (motor68k,
motor6502, motorz80, motordcpu16, motormips, motorschip), the librarian
(xlib) and the linker (xlink). Build system: CMake.

License: GPL-3.0-or-later
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class AsmotorConan(ConanFile):
    name = "asmotor"
    version = "1.0.0"
    description = "Portable and generic assembler engine and development system (680x0/6502/MIPS32/Z80/GameBoy/DCPU-16/CHIP-8)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/asmotor/asmotor"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def validate(self):
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        # 主源码 tarball（release/1.0.0 官方 tag）
        get(
            self,
            url=self.conan_data["sources"]["url"],
            sha256=self.conan_data["sources"]["sha256"],
            strip_root=True,
        )
        # util/ 是官方 git 子模块（asmotor-util @ 3dfef30），官方 tarball 不含，
        # 按 release/1.0.0 引用的精确提交单独下载补齐（同上 actiona/3rdparty 子模块模式）。
        get(
            self,
            url=self.conan_data["sources"]["util_url"],
            sha256=self.conan_data["sources"]["util_sha256"],
            destination="util",
            strip_root=True,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        # ucm.cmake 内 cmake_minimum_required 低于 CMake 3.5，CMake 4.x 已移除兼容，
        # 需要显式声明 policy 下限（实测必须，否则 "Compatibility with CMake < 3.5 has been removed"）。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 删除上游注释掉的冗余（无）

    def package_info(self):
        # 命令行工具链，非库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]