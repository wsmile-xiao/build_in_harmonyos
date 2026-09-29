#!/usr/bin/env python3
"""Conan recipe — vosk-api 0.3.50 for HarmonyOS PC (os=OHOS, arch=armv8, clang).

Vosk 是离线开源语音识别工具箱。本配方构建其 C API 库 `libvosk.so`
（上游 src/*.cc，C++17）并安装头文件 `src/vosk_api.h`；仓库内的
Python / Java / C# / Node / Rust bindings 不在本包交付面内，它们都是
libvosk.so 的消费者。

依赖链：

    vosk-api ──> kaldi/g20231112 ──> openfst/1.8.4, openblas/0.3.34
             └─> libfstngram/1.8.4

  * kaldi：静态库（libkaldi-*.a），提供 decoder/online2/rnnlm/lat 等 vosk 需要的模块；
  * openfst + libfstngram：FST 与 NGramFst(LOUDS) 扩展。src/model.cc 直接
    `#include <fst/extensions/ngram/ngram-fst.h>` 并注册
    `FstRegisterer<NGramFst<StdArc>>`，因此 libfstngram 是硬依赖——
    openfst/1.8.4 本体按上游默认（--enable-ngram-fsts 关闭）不带 ngram 扩展；
  * openblas：kaldi 的 BLAS/LAPACK 后端（shared-library，由 Conan 传播）。

适配点（见 patches/）：
  1. CMakeLists.txt：补入上游漏写的 src/postprocessor.cc（vosk_api.cc 的
     vosk_text_processor_* 引用其 Processor 符号），并把链接目标换成 Conan
     交付的 kaldi::kaldi / libfstngram::libfstngram；
  2. src/recognizer.cc：WordAlignLatticePartial -> WordAlignLattice
     （kaldi g20231112 已把 partial 变体合并进同一入口）。

库形态：libvosk.so。上游 src/Makefile 也默认 `--shared`，C API 的典型用法是
被 ctypes / 其它语言绑定 dlopen，故按动态库交付（libvosk 非系统同名库，R26 不适用），
运行时依赖由 Conan 依赖链传播。

上游测试：上游 0.3.50 无自动化测试套件（源码树无 tests/ 目录，无 ctest/pytest/
gtest 注册，.travis.yml 只构建 wheel）。真实测试入口是 c/Makefile 的
`test_vosk` / `test_vosk_speaker`（c/test_vosk.c / c/test_vosk_speaker.c），
两者都需要外部下载的模型目录与 test.wav，属人工验证程序，不纳入本配方 build()。
本配方的验证由 test_package/ 承担（消费者功能测试 + 鸿蒙专项测试）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class VoskApiConan(ConanFile):
    name = "vosk-api"
    version = "0.3.50"
    description = ("Offline open source speech recognition toolkit: C API "
                   "library (libvosk) built on Kaldi and OpenFst")
    license = "Apache-2.0"
    homepage = "https://github.com/alphacep/vosk-api"
    url = "https://github.com/alphacep/vosk-api"
    topics = ("speech-recognition", "asr", "kaldi", "vosk")

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须用 in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"vosk-api 仅适配 Linux / OHOS，当前 os={self.settings.os}")

    def requirements(self):
        self.requires("kaldi/g20231112")
        # src/model.cc 等直接 include <fst/...>，显式声明直接依赖
        self.requires("openfst/1.8.4")
        # src/model.cc 注册 NGramFst<StdArc>，需要 ngram 扩展库与头文件
        self.requires("libfstngram/1.8.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # E225: 不往源码树写 CMakeUserPresets.json
        tc.user_presets_path = False
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.generate()
        # OHOS 上 make 无法创建 jobserver FIFO（Operation not permitted），
        # 串行构建以免 jobserver 告警与内存超订。
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["vosk"]
        self.cpp_info.set_property("cmake_file_name", "vosk")
        self.cpp_info.set_property("cmake_target_name", "vosk::vosk")
