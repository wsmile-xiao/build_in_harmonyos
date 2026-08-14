#!/usr/bin/env python3
"""Conan test_package — game-music-emu 0.6.5 consumer test.

Consumer 视角: find_package(game-music-emu) + gme::gme，端到端验证 C API。
测试数据 test.nsf 取自上游发布包（1 轨 NSF）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GameMusicEmuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = arch_map.get(
                str(self.settings.arch), str(self.settings.arch)
            )
            # -static 只适用于静态库链接；shared 构建会与 libgme.so 冲突
            if not self.dependencies["game-music-emu"].options.shared:
                tc.extra_exelinkflags.append("-static")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "gme_test")
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the OHOS test package"
                )
            self.run(f'"{qemu}" "{bin_path}"', env="conanrun")
        else:
            self.run(bin_path, env="conanrun")
