#!/usr/bin/env python3
"""Conan recipe — milkytracker 1.06 (MilkyTracker).

MilkyTracker 是一个跨平台音乐制作工具（MOD/XM tracker），GPLv3，
CMake 构建系统，C++11。硬依赖 SDL2（find_package(SDL2 REQUIRED) +
SDL2::SDL2 target）；zlib/lhasa/zziplib/ALSA/JACK/RtMidi 均为可选
（find_package 不带 REQUIRED，找不到时对应功能自动禁用）。

OHOS 适配要点：
  - sdl2 配方只声明 libs，未声明 cmake 属性 → 在此处重写
    cmake_file_name/cmake_target_name 为 SDL2 / SDL2::SDL2，
    匹配上游 find_package(SDL2) 的用法；
  - sdl2 包头文件位于 include/SDL2/，上游源码 #include <SDL.h>，
    因此把 include/SDL2 加入 includedirs；
  - 产物为可执行文件，package() 内需用 binary-sign-tool 签名，
    否则 test_package 运行报 Operation not permitted。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

import os


class MilkytrackerConan(ConanFile):
    name = "milkytracker"
    version = "1.06"
    description = "MilkyTracker - music creation tool inspired by Fast Tracker 2"
    license = "GPL-3.0-or-later"
    homepage = "https://milkytracker.titandemo.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游用 find_package(SDL2 REQUIRED) + target SDL2::SDL2
        sdl2 = self.dependencies["sdl2"]
        sdl2.cpp_info.set_property("cmake_file_name", "SDL2")
        sdl2.cpp_info.set_property("cmake_target_name", "SDL2::SDL2")
        # sdl2 头文件在 include/SDL2/，上游源码用 #include <SDL.h>
        # Conan 2 要求绝对路径（相对包目录拼接）
        sdl2_pkg = sdl2.package_folder
        sdl2.cpp_info.includedirs = [
            os.path.join(sdl2_pkg, "include/SDL2"),
            os.path.join(sdl2_pkg, "include"),
        ]

        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # CMake 4.x 兼容：上游 cmake_minimum_required(3.10)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake 不识别 HarmonyOS 平台，用 Linux 兼容（仓库多库先例）
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # OHOS ELF 必须签名，否则 test_package 运行报 Operation not permitted
        self._sign_binaries()

    def _sign_binaries(self):
        import glob
        import os
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in glob.glob(os.path.join(bindir, "*")):
            if not os.path.isfile(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
