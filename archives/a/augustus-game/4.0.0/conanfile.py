#!/usr/bin/env python3
"""Conan recipe for augustus-game 4.0.0 — Caesar 3 引擎开源重制（SDL2 游戏，CMake 构建）.

augustus 是 Julius 的改进分支（Caesar 3 开源重制），构建产物为可执行程序 bin/augustus。

要点：
- 上游自带 MODULE 模式 FindSDL2/FindSDL2_mixer cmake 模块（非 CONFIG），
  CMAKE_PREFIX_PATH 对它无效 → 通过 CMake 缓存变量直接注入依赖路径。
- 设备用户前缀可能提供只导出小写变量的 EXPATConfig.cmake；补丁 0005
  此时回退到上游内置 expat，避免误判外部依赖可用后丢失头文件。
- 鸿蒙沙箱无 OSS/dsp 音频设备，SDL_Init 报 "dsp: No such audio device" 属环境限制。
  补丁 0004 为程序增加无头 --version 出口（SDL 初始化前打印版本退出 0），
  供 L2 smoke test 与 test_package 验证。
- 补丁 0002 调整链接顺序：静态链接时 SDL2_mixer 先于 SDL2，符号按依赖序解析。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class AugustusgameConan(ConanFile):
    name = "augustus-game"
    version = "4.0.0"
    description = "Caesar 3 游戏引擎开源重制版 Augustus（Julius 改进分支），C 语言 + SDL2"
    license = "AGPL-3.0-only"
    homepage = "https://github.com/Keriew/augustus"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # 交叉编译环境下依赖 conanbuild 环境显式注入编译器（避 PATH 巧合性正确）
    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 当前 main 收录两个静态库配方；发布状态由 W0 recipe download 复验。
        self.requires("sdl2/2.30.10")
        self.requires("sdl2_mixer/2.8.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # CI worker 网络瞬时抖动加固：conan 层显式重试（默认仅2次）；
        # 镜像回退由 CI 注入层负责，sources.url 保持纯官方 URL
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=5, retry_wait=10)

    def _sdk_llvm_libdir(self):
        # CI shell 预置的 LD_LIBRARY_PATH（如 ~/usr/local/lib）会遮蔽 lld 的
        # RUNPATH($ORIGIN/../lib)，导致 SDK 自带 ABI 匹配的 libxml2.so.16 加载失败。
        # 从实际编译器路径推导 llvm/lib 并校验，找不到则返回空（跳过守卫，不抛异常）。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or shutil.which("clang")
        if not cc:
            self.output.info("未定位到 C 编译器，跳过 OHOS SDK 链接运行时守卫")
            return ""
        sdk_lib = os.path.normpath(os.path.join(
            os.path.dirname(os.path.realpath(cc)), os.pardir, "lib"
        ))
        if not os.path.isfile(os.path.join(sdk_lib, "libxml2.so.16")):
            self.output.info("llvm/lib 下无 libxml2.so.16，跳过 OHOS SDK 链接运行时守卫")
            return ""
        return sdk_lib

    def _build_environment(self):
        environment = Environment()
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    @staticmethod
    def _header_dir(package_folder, header_name):
        candidates = (
            os.path.join(package_folder, "include", "SDL2"),
            os.path.join(package_folder, "include"),
        )
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, header_name)):
                return candidate
        return candidates[0]

    def generate(self):
        tc = CMakeToolchain(self)
        sdl2 = self.dependencies["sdl2"]
        mixer = self.dependencies["sdl2_mixer"]
        sdl2_inc = self._header_dir(sdl2.package_folder, "SDL.h")
        sdl2_lib = os.path.join(sdl2.package_folder, "lib")
        mixer_inc = self._header_dir(mixer.package_folder, "SDL_mixer.h")
        mixer_lib = os.path.join(mixer.package_folder, "lib")
        # 上游 MODULE 模式 FindSDL2/FindSDL2_mixer 不消费 CMAKE_PREFIX_PATH；
        # 预置其模块读取的缓存变量，FIND_PATH/FIND_LIBRARY 见缓存已存在即跳过搜索。
        # SDL2_LIBRARY_TEMP 一并预置：FindSDL2 尾部以它为准回写 SDL2_LIBRARY，
        # 避免 FIND_LIBRARY 意外命中系统同名库覆盖注入值。
        tc.variables["SDL2_INCLUDE_DIR"] = sdl2_inc
        tc.variables["SDL2_LIBRARY"] = os.path.join(sdl2_lib, "libSDL2.a")
        tc.variables["SDL2_LIBRARY_TEMP"] = os.path.join(sdl2_lib, "libSDL2.a")
        tc.variables["SDL2_MIXER_INCLUDE_DIR"] = mixer_inc
        tc.variables["SDL2_MIXER_LIBRARY"] = os.path.join(mixer_lib, "libSDL2_mixer.a")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # 守卫 lld 链接探测阶段的 libxml2 加载（对齐 abseil 配方模式）
        with self._build_environment().vars(self).apply():
            cmake.configure()
            # 上游已内建 -Werror=implicit-function-declaration 等严格开关
            # OHOS CI 的 make jobserver FIFO 受限，且多任务编译可能耗尽真机内存。
            cmake.build(cli_args=["--parallel", "1"])

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.install()

    def package_info(self):
        # 可执行程序包：无链接库，消费者只需 bin/
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
