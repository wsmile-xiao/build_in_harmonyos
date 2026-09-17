#!/usr/bin/env python3
"""Conan recipe — OpenJazz 20260301 (Jazz Jackrabbit 1 游戏引擎重制)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class OpenJazzConan(ConanFile):
    name = "openjazz"
    version = "20260301"
    description = "Jazz Jackrabbit 1 game engine reimplementation"
    license = "GPL-2.0"
    homepage = "https://alister.eu/jazz/oj/"
    url = "https://github.com/AlisterT/openjazz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092：HarmonyOS 不是上游 CMake 已知平台，沿用 UNIX 分支。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["SDL_VERSION"] = "2"
        # sdl2/2.30.10 的原生 config 提供 SDL2::SDL2；避免 CMakeDeps
        # 默认生成的 sdl2::sdl2 与上游 target 名不一致。
        sdl2 = self.dependencies["sdl2"]
        tc.variables["SDL2_DIR"] = os.path.join(sdl2.package_folder, "lib", "cmake", "SDL2")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
