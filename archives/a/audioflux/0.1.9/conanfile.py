#!/usr/bin/env python3
"""Conan recipe — audioflux 0.1.9 (C core + Python wrapper, CMake build).

audioflux 是音频/音乐分析特征提取库：C 核心（src/，CMake 构建共享库
libaudioflux.so，OpenMP 加速）+ Python 包装（python/audioflux/，经 ctypes
加载 libaudioflux.so，非 pybind11、无 .pyx）。

适配要点：
- C 核心 CMakeLists 原无 OHOS 分支（HarmonyOS 落到分支外无目标生成），
  补丁 0001-ohos-cmake-branch.patch 新增 HarmonyOS|OHOS 分支：编译器由
  Conan CMakeToolchain 提供（R33），OpenMP 用 OHOS SDK 自带 libomp
  （-fopenmp=libomp 自动链接），产物 libaudioflux.so 安装到 lib/。
- Python 包装打包进 lib/python3.12/site-packages/audioflux/，其中
  lib/libaudioflux.so 由 fftlib.py（ctypes.cdll.LoadLibrary）按包内 lib/
  目录加载；同份 .so 另装 lib/ 供 C 消费者直接链接。
- 上游公开头文件（include/*.h，如 flux_base.h/bft_algorithm.h）装到
  include/audioflux/ 供 C 层消费者使用。
- 上游无独立测试套件（git tree 0 test 文件，仅 benchmark/ 脚本与
  docs/examples.md 文档），不产 CLI（R38 不适用）。
"""

import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class AudiofluxConan(ConanFile):
    name = "audioflux"
    version = "0.1.9"
    description = "A library for audio and music analysis, feature extraction (C core + Python ctypes wrapper)"
    license = "MIT"
    homepage = "https://github.com/libAudioFlux/audioFlux"
    url = ""  # CI fills this
    topics = ("audio", "music-analysis", "feature-extraction", "ctypes")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS：conan 适配版 CMakeToolchain 自动映射 CMAKE_SYSTEM_NAME=HarmonyOS，
        # 命中补丁新增的 HarmonyOS 分支；显式保持 aarch64。
        # E383（knowledge/graph/E383.kv）：CMake 4.x 无 Platform/HarmonyOS.cmake 模块，
        # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空 → 共享库无 DT_SONAME（L5 soname_gate 失败）。
        # 显式注入 -Wl,-soname, 使 SOVERSION 生效（同 yajl/libyajl.so 先例）。
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMake 工程根在源码 src/ 子目录（project(audioflux) + add_library 全在 src/CMakeLists.txt）
        cmake.configure(build_script_folder="src")
        cmake.build()
        # 复制 .so 进 python 包内 lib/（fftlib.py 从此目录 ctypes 加载）
        so = os.path.join(self.cpp.build.bindirs[0], "libaudioflux.so")
        if not os.path.exists(so):
            raise RuntimeError(f"libaudioflux.so 未生成: {so}")
        dst = os.path.join(self.source_folder, "python", "audioflux", "lib")
        os.makedirs(dst, exist_ok=True)
        shutil.copy2(so, os.path.join(dst, "libaudioflux.so"))

    def package(self):
        # C 库产物：libaudioflux.so（符号链接）+ 实文件 libaudioflux.so.0.1.9 → lib/
        # （仅复制符号链接会导致包内悬空链接，静态签名校验/下游 dlopen 均失败——
        # R04 强制静态分支实测发现，故实文件必须一并进包），公开头文件 → include/audioflux/
        for name in ("libaudioflux.so", "libaudioflux.so.0.1.9"):
            copy(self, name, src=self.cpp.build.bindirs[0],
                 dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include", "audioflux"))
        # Python 包装 → lib/python3.12/site-packages/audioflux/
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        copy(self, "*", src=os.path.join(self.source_folder, "python", "audioflux"),
             dst=os.path.join(site, "audioflux"), keep_path=True)

    def package_info(self):
        self.cpp_info.libs = ["audioflux"]
        # 运行期环境：PYTHONPATH 指向 site-packages，LD_LIBRARY_PATH 指向 lib/
        self.cpp_info.set_property("cmake_file_name", "audioflux")
        self.cpp_info.set_property("cmake_target_name", "audioflux::audioflux")
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.env_info.PYTHONPATH = site
