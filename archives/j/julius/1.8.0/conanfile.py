#!/usr/bin/env python3
"""Conan recipe — julius 1.8.0 (Caesar III 重制版游戏).

julius 是 Caesar III 的开源重制版（纯 C / CMake / AGPL-3.0，bvschaik/julius）。
SDL2 图形 + SDL_mixer 音频输出，无音频输入。构建依赖 sdl2/2.30.10 与
sdl2_mixer/2.8.1（两者均已 OHOS 适配并发布到 ohpcd）；libpng 可选（无系统
libpng 时自动回退捆绑 ext/png + ext/zlib，不声明 conan 依赖）。

OHOS 适配要点：
  - 上游用自带模块模式 cmake/FindSDL2.cmake / FindSDL2_mixer.cmake 查找依赖
    （module mode，不走 CMakeDeps config），需在 generate() 显式注入
    SDL2_INCLUDE_DIR / SDL2_LIBRARY / SDL2_MIXER_INCLUDE_DIR /
    SDL2_MIXER_LIBRARY 四个 cache 变量，指向两个依赖包 package_folder 的
    include/SDL2 与 lib/libSDL2.a / lib/libSDL2_mixer.a（sdl2_mixer 2.8.1
    配方同款做法）；
  - E092：CMake 不识别 HarmonyOS 平台，CMAKE_SYSTEM_NAME=Linux（仓库多库先例）；
  - CMake 4.x：上游 cmake_minimum_required(3.1)，设
    CMAKE_POLICY_VERSION_MINIMUM=3.5 双保险（milkytracker/sdl2_mixer 先例）；
  - R9/HMDFS：cmake.build() 用 --parallel 1 规避 make jobserver mkfifo 坑；
  - 上游 36 个 CTest 集成测试（autopilot savegame 语义比较，每用例=1 断言点）
    在 build() 用 cmake.test(build_tool_args=["-j1"]) 真实执行（L1c），
    任一失败即 conan create 失败；
  - 产物 bin/julius 为可执行文件，package() 内需 llvm-objcopy --remove-section
    .codesign + binary-sign-tool sign -selfSign 1 自签（milkytracker 先例），
    否则 test_package 运行报 Operation not permitted；
  - CI worker 沙箱兼容：平台 buildbot worker（AppSpawn，USER=100）的动态加载器
    无法按 lld 的 RUNPATH($ORIGIN/../lib) 命中 OHOS SDK llvm/lib，导致 lld 加载
    libxml2.so.16 失败（Error loading shared library / Error relocating ...
    symbol not found，编译链在 CMake 编译器自检即断）。build() 通过
    clang -print-resource-dir 动态推导 SDK llvm/lib 前缀并注入 LD_LIBRARY_PATH，
    让加载器优先命中 SDK 自带 libxml2.so.16；推导失败或目录缺文件时优雅降级
    （不注入、不报错），全程不硬编码任何绝对路径（R33）。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class JuliusConan(ConanFile):
    name = "julius"
    version = "1.8.0"
    description = "Julius - open source re-implementation of Caesar III"
    license = "AGPL-3.0"
    homepage = "https://github.com/bvschaik/julius"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("sdl2_mixer/2.8.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # CMake 4.x 兼容 + E092 平台绕过（仓库多库先例）
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # julius 自带模块模式 FindSDL2.cmake / FindSDL2_mixer.cmake（module mode），
        # 显式注入模块查找所需的 cache 变量（指向依赖包 package_folder）
        sdl2 = self.dependencies["sdl2"]
        sdl2_pkg = sdl2.package_folder
        if sdl2_pkg:
            tc.cache_variables["SDL2_INCLUDE_DIR"] = os.path.join(sdl2_pkg, "include/SDL2")
            tc.cache_variables["SDL2_LIBRARY"] = os.path.join(sdl2_pkg, "lib/libSDL2.a")

        mixer = self.dependencies["sdl2_mixer"]
        mixer_pkg = mixer.package_folder
        if mixer_pkg:
            tc.cache_variables["SDL2_MIXER_INCLUDE_DIR"] = os.path.join(mixer_pkg, "include/SDL2")
            tc.cache_variables["SDL2_MIXER_LIBRARY"] = os.path.join(mixer_pkg, "lib/libSDL2_mixer.a")

        # make test → ctest 带失败详情输出（L1c 日志痕迹更清晰）
        tc.cache_variables["CMAKE_CTEST_ARGUMENTS"] = "--output-on-failure"

        tc.generate()

    def _sdk_llvm_lib_dir(self):
        """推导 OHOS SDK llvm/lib 目录（含 libxml2.so.16）。

        clang -print-resource-dir 输出 <sdk>/llvm/lib/clang/<version>，
        dirname 两次即 <sdk>/llvm/lib（libxml2.so.16 所在目录）。
        仅当该目录确实含 libxml2.so.16 才返回，否则返回 None 优雅降级。
        """
        cc_map = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_map.get("c") or cc_map.get("cpp")
        if not cc:
            return None
        try:
            out = subprocess.check_output(
                [cc, "-print-resource-dir"], stderr=subprocess.DEVNULL, text=True
            ).strip()
        except Exception:
            return None
        lib = os.path.dirname(os.path.dirname(out))
        if lib and os.path.isfile(os.path.join(lib, "libxml2.so.16")):
            return lib
        return None

    def build(self):
        apply_conandata_patches(self)

        # CI worker 沙箱兼容：注入 SDK llvm/lib 到 LD_LIBRARY_PATH，
        # 使 lld 优先加载 SDK 自带 libxml2.so.16（见 docstring 说明）。
        sdk_lib = self._sdk_llvm_lib_dir()
        if sdk_lib:
            old = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = sdk_lib + ((":" + old) if old else "")
            self.output.info("Injected SDK llvm/lib into LD_LIBRARY_PATH: %s" % sdk_lib)

        cmake = CMake(self)
        cmake.configure()
        # R9: OHOS 并行约束，单线构建规避 HMDFS mkfifo / Operation not permitted
        cmake.build(cli_args=["--parallel", "1"])
        # L1c: 上游 36 个 CTest 集成测试真实执行；失败即 conan create 失败
        cmake.test(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # OHOS ELF 必须自签，否则 test_package 运行报 Operation not permitted
        self._sign_binaries()

    def _sign_binaries(self):
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
