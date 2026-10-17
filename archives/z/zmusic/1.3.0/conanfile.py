#!/usr/bin/env python3
"""Conan recipe — zmusic 1.3.0（GZDoom 音乐系统独立库，CMake/C++，鸿蒙 PC aarch64 移植）。

上游: https://github.com/ZDoom/zmusic (tag 1.3.0)
产物: libzmusic.so  —— 完整版（含 ADL/OPN/Timidity/WildMidi/OPL 等合成器，GPLv3）
      libzmusiclite.so —— 精简版（仅保留 FluidSynth，规避 GPL 传染）
依赖: glib/2.88.3.1 —— 内置 thirdparty/fluidsynth 通过
      pkg_search_module(GLIB REQUIRED glib-2.0) 强制要求，缺失则 configure 直接失败
      libsndfile/1.2.2、mpg123/1.33.5 —— 上游 DYN_SNDFILE/DYN_MPG123 默认 ON 走
      dlopen 运行时加载；OHOS 上 dlopen 第三方 .so 不可靠，故关闭动态加载，
      改由上游 cmake/FindSndFile.cmake、cmake/FindMPG123.cmake 直接链接已适配包
上游测试: 上游无 tests/ 目录、无 ctest 注册、README 未提及测试（已清点），
          因此由 test_package 承担消费者视角的鸿蒙特有测试。
适配点: 无源码补丁。核心适配工作为依赖注入（glib via PkgConfigDeps）与
        关闭 dlopen 型动态加载（改为链接期绑定）。
"""
import os
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import build_jobs
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps

# OHOS 构建目录位于 HMDFS，偶发在首批编译单元上出现"静默失败"：make 报
# Error 1 但 clang 没有任何 error: 输出，同一命令手工/重跑即成功（属环境资源
# 竞争，非源码或编译器问题）。失败后重试即可收敛，重试次数上限防止掩盖真实错误。
BUILD_RETRIES = 3


class ZmusicConan(ConanFile):
    name = "zmusic"
    version = "1.3.0"
    description = "GZDoom's music system as a standalone library"

    license = "GPL-3.0"
    homepage = "https://github.com/ZDoom/zmusic"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 内置 fluidsynth 的硬依赖：thirdparty/fluidsynth/src/CMakeLists.txt
        #   pkg_search_module(GLIB REQUIRED glib-2.0)
        self.requires("glib/2.88.3.1")
        # 关闭 DYN_* 后由上游 find_package(SndFile) / find_package(MPG123) 直接链接
        self.requires("libsndfile/1.2.2")
        self.requires("mpg123/1.33.5")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = arch_map.get(
                str(self.settings.arch), str(self.settings.arch)
            )
        tc.cache_variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游默认 ON（运行时 dlopen）；OHOS 下改为链接期绑定，保证解码器真实可用
        tc.cache_variables["DYN_SNDFILE"] = "OFF"
        tc.cache_variables["DYN_MPG123"] = "OFF"
        tc.generate()
        # glib 以 pkg-config 方式被内置 fluidsynth 查找，必须生成 .pc 并注入
        # PKG_CONFIG_PATH，否则 cmake 的 pkg_search_module(GLIB REQUIRED) 失败
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 并行度收敛到 4：上游 thirdparty 含 adlmidi/nuked_opl3/inst_db 等超大
        # 翻译单元，单实例内存占用高；conan 默认按 CPU 核数（本机 20）并行风险大。
        # 注：不能用 CMake.build(build_tool_args=["--", "-jN"])：该参数是**追加**在
        # 默认 "-j<核数>" 之后，且带 "--" 会让 make 把 -jN 当成目标名。
        jobs = max(1, min(int(build_jobs(self)), 4))
        cmd = f'cmake --build "{self.build_folder}" -- -j{jobs}'
        # env 显式继承 os.environ：其中包含 Conan 在执行 build() 前已激活的
        # conanbuild 环境（profile 的 [buildenv]，以及 PkgConfigDeps 写入的
        # PKG_CONFIG_PATH —— 若丢失，内置 fluidsynth 的 pkg_search_module(GLIB)
        # 在增量重编译时可能找不到 glib-2.0.pc）。此处用 copy() 而非裸引用，
        # 避免子进程对环境字典产生副作用。
        build_env = os.environ.copy()
        for attempt in range(1, BUILD_RETRIES + 1):
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                  cwd=self.build_folder, env=build_env)
            if proc.returncode == 0:
                if proc.stdout:
                    self.output.info(proc.stdout[-2000:])
                break
            tail = (proc.stdout or "") + (proc.stderr or "")
            # 真实错误快速失败：日志里出现编译器诊断（error:）说明是源码/配方问题，
            # 不是本环境的"静默失败"，此时重试只会掩盖问题，直接抛出。
            if "error:" in tail:
                raise ConanException(
                    f"cmake --build 报出编译器错误（非环境性静默失败），"
                    f"不重试，尾部输出:\n{tail[-4000:]}"
                )
            self.output.warning(
                f"构建第 {attempt}/{BUILD_RETRIES} 次失败（rc={proc.returncode}），"
                f"日志无 error: 输出，属 HMDFS 环境偶发资源竞争，输出尾部:\n{tail[-2000:]}"
            )
            if attempt == BUILD_RETRIES:
                raise ConanException(
                    f"cmake --build 连续 {BUILD_RETRIES} 次失败且始终无 error: 输出，"
                    f"尾部输出:\n{tail[-4000:]}"
                )
            time.sleep(5)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["zmusic", "zmusiclite"]
        self.cpp_info.set_property("cmake_file_name", "zmusic")
        self.cpp_info.set_property("cmake_target_name", "ZMusic::zmusic")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
