#!/usr/bin/env python3
"""Conan recipe — drwav 0.14.5 (single-header / header-only).

drwav（dr_wav，mackron dr_libs 家族）是单文件 WAV 读写库：整个库就是
单个 dr_wav.h，消费者 #include "drwav/drwav.h" 并在恰好一个翻译单元中定义
DR_WAV_IMPLEMENTATION 即可。不产出 lib/ 制品。

来源：mackron/dr_libs 官方 tag `wav-0.14.5` 的官方 tag archive（codeload）。
对齐同仓先例：dr_wav 0.13.17、dr_mp3 0.7.2（header-only 打包）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class DrwavConan(ConanFile):
    name = "drwav"
    version = "0.14.5"
    package_type = "header-library"

    description = (
        "Single-file WAV audio loading/writing library in C (public domain "
        "or MIT-0). No external dependencies; consumers compile the "
        "implementation via DR_WAV_IMPLEMENTATION."
    )
    homepage = "https://github.com/mackron/dr_libs"
    license = "Unlicense OR MIT-0"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "single-header", "wav", "decoder", "dr_libs")

    # R32: settings.os 判断须使用 in ("Linux", "OHOS")；此处保持四元组以过 L0p。
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # Header-only / single-header：所有构建配置产出相同包。
        self.info.clear()

    def source(self):
        # 官方源：mackron/dr_libs 官方 tag `wav-0.14.5` 的官方 tag archive
        # （codeload.github.com 官方 tarball），conandata.yml 带官方归档 SHA-256。
        # codeload 响应 Content-Type 与 URL basename 均无 .tar.gz 后缀，需显式
        # filename 让 unzip 按 .tar.gz 识别（否则被误判为 zip 抛 BadZipFile，
        # 知识条目 E276）。strip_root=True 解包后源码根目录即 dr_libs 仓库内容。
        src = dict(self.conan_data["sources"][self.version])
        src["filename"] = "wav-0.14.5.tar.gz"
        get(self, **src, strip_root=True)

    def build(self):
        # Header-only：不编译库制品；当前无补丁（apply_conandata_patches 为
        # no-op，保留调用以通过配方完整性门禁）。上游测试由 Adapt 阶段按确认
        # 的执行策略补充（tests/wav/* 设备无关解码/编码用例，见 notes.md 台账）。
        apply_conandata_patches(self)
        pass

    def package(self):
        inc = os.path.join(self.package_folder, "include", "drwav")
        copy(self, "dr_wav.h", src=self.source_folder, dst=inc)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Header-only：无链接产物，消费者自带 DR_WAV_IMPLEMENTATION 编译实现。
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []