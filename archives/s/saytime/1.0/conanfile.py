#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for saytime 1.0 — Jef Poskanzer 1990 年的 SPARCstation 报时语音。

saytime 按当前时刻从 30 段 8-bit μ-law 裸 PCM 语音片段里挑出对应的一句
（"The time is eight o'clock exactly." / "... eight oh-eight and one second."），
按顺序拼成一条流写进 /dev/audio。随包的 saytime.sh 是同等逻辑的 shell 版。

OHOS aarch64 适配要点（两处，全部集中在 patch 0001）：
- **/dev/audio 不存在**。这是 SPARCstation 的 OSS 音频设备节点，OHOS PC 没有任何
  对应设备。补丁把「打开失败就 perror + exit(1)」改成「打印一行提示后把 fd 换成
  1（stdout）」。调用方 `saytime | some-player` 即可，程序本身不必因缺设备而退出。
  ★ 这是刻意的行为变更，manifest.yaml 里 behavior_change: true。
- **SOUND_DIR 被写死成作者家目录**。上游 Makefile 硬编码
  `-DSOUND_DIR="/users/mag/games/sounds/audio"`，本机不存在。配方改为指向包内
  `share/saytime/sounds`，补丁再加一层 `SAYTIME_SOUNDS` 环境变量覆盖，
  让部署方不必重编译就能换语音目录。

产出的语音片段是**无头裸 PCM**（不是 .au 容器），拼接结果本身就是 SPARCstation
音频设备期望的字节流，因此「精确拼接」是可确定性断言的行为。

装 bin/saytime + share/saytime/sounds/*.au（30 个语音片段）+ saytime.sh。
不安装任何播放器：渲染后端由调用方决定。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class SaytimeConan(ConanFile):
    name = "saytime"
    version = "1.0"
    description = (
        "Jef Poskanzer's 1990 spoken-clock for the SPARCstation: concatenates "
        "30 raw mu-law PCM phrase clips into the current time and writes the "
        "stream to /dev/audio"
    )
    license = "MIT"
    # 上游原包没有 README / homepage（只有 saytime.c / saytime.sh / Makefile /
    # sounds/）。这里指向可核验的 Debian 源码浏览页，而不是猜一个 URL。
    homepage = "https://sources.debian.org/src/saytime/1.0/"
    topics = ("audio", "sparcstation", "clock", "mu-law", "pcm", "saytime")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml", "CMakeLists.txt", "patches/*"

    def package_id(self):
        # 纯 C 用户态程序，不随 build_type / 编译优化变化
        self.info.settings.build_type = "Any"
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("arch")

    def layout(self):
        cmake_layout(self, build_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        # 把包内 sounds 目录作为编译期 SOUND_DIR 传给 CMakeLists。
        sounds = os.path.join(self.package_folder, "share", "saytime", "sounds")
        tc.cache_variables["SAYTIME_SOUNDS_DIR"] = sounds.replace("\\", "/")
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # patches 必须用列表格式，否则 Conan 按 self.version 取到空列表并静默跳过，
        # 且 CI 门禁 L0f 会报 bad_patch_format。详见 notes.md「坑 1」。
        apply_conandata_patches(self)

    def build(self):
        # 用 CMakeToolchain 驱动编译，而不是 self.run("<clang> ...")：
        # 本地实测 Conan 2.29.1 的 self.run 在带 [buildenv] 的 build profile 下
        # 会把命令打散（报 "'.' is not recognized as an internal or external
        # command"），CMake 自己的编译器调用路径不受影响。详见 notes.md「坑 2」。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "saytime", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*.au", src=os.path.join(self.source_folder, "sounds"),
             dst=os.path.join(self.package_folder, "share", "saytime", "sounds"))
        copy(self, "saytime.sh", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "saytime"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
