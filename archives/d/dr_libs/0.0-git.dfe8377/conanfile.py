#!/usr/bin/env python3
"""Conan recipe — dr_libs 0.0-git.dfe8377 (mackron single-header audio
decoding library collection: dr_wav / dr_flac / dr_mp3).

dr_libs 是 mackron 维护的单头音频解码库集合，一个仓库同时交付三个
互相独立的单头库（tarball 根目录三头并列）：
  - dr_wav.h  0.14.6  WAV 读写（DR_WAV_IMPLEMENTATION）
  - dr_flac.h 0.13.4  FLAC 解码（DR_FLAC_IMPLEMENTATION）
  - dr_mp3.h  0.7.4   MP3 解码（DR_MP3_IMPLEMENTATION）
每个头都是零依赖、可移植 C89/C99，消费者在恰好一个翻译单元中定义对应
的 IMPLEMENTATION 宏即可把实现编译进自身，不产出 lib/ 制品。

形态：header-only（三头各自独立）。本包是三合一聚合包，归档打包三头；
同仓已有按单头拆分的兄弟包（dr_wav 0.13.17 / drwav 0.14.5 / dr_flac
0.12.39 / dr_mp3 0.7.2，各自只交付单头），本包为需要整套 dr_libs 的
消费者提供一次依赖三头全量的入口。

版本号依据：上游 master-only，各头独立 tag 而仓库无整仓版本号。快照
master @
  dfe8377631000664666519fdb83da193fd8037f4 → 0.0-git.dfe8377
（git ls-remote 实测 master HEAD；7-hex 前缀 dfe8377 = 版本锚点）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class DrLibsConan(ConanFile):
    name = "dr_libs"
    version = "0.0-git.dfe8377"
    package_type = "header-library"

    description = (
        "Single-header audio decoding library collection by mackron: "
        "dr_wav (WAV read/write), dr_flac (FLAC decode), dr_mp3 (MP3 "
        "decode). Zero dependencies, public domain or MIT-0; consumers "
        "compile each implementation via the per-header *_IMPLEMENTATION "
        "macro."
    )
    homepage = "https://github.com/mackron/dr_libs"
    license = "Unlicense OR MIT-0"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "single-header", "wav", "flac", "mp3", "decoder",
              "dr_libs", "header-only")

    # R32: settings.os 判断须使用 in ("Linux", "OHOS")；此处保持四元组以过 L0p。
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # Header-only：所有构建配置产出相同包。
        self.info.clear()

    def source(self):
        # conandata 镜像列表（ghfast.top 在前，官方 GitHub 兜底）；
        # sha256 本机双实测（镜像与官方两 URL 内容逐字节一致）。
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only：不编译库制品；当前无补丁（apply_conandata_patches
        # 为 no-op，保留调用以通过配方完整性门禁）。三头的实现段编译由
        # test_package 消费侧真实覆盖：test_dr_libs.c 在同一翻译单元同时
        # 激活三个 *_IMPLEMENTATION 宏，OHOS clang 下全量编译三头实现段。
        apply_conandata_patches(self)

    def package(self):
        # 许可证（Unlicense / MIT-0 双许可原文）
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 三头 → include/ 根（tarball 根目录三头并列，消费者
        # #include "dr_wav.h" / "dr_flac.h" / "dr_mp3.h" 直接可用；
        # 三头互相独立，无子目录布局）
        copy(self, "dr_wav.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "dr_flac.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "dr_mp3.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        # Header-only：无链接产物；消费者按需在恰好一个 TU 中定义
        # DR_WAV_IMPLEMENTATION / DR_FLAC_IMPLEMENTATION / DR_MP3_IMPLEMENTATION。
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
