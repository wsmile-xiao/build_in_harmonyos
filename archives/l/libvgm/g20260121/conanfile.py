#!/usr/bin/env python3
"""Conan recipe for libvgm g20260121 — Video Game Music playback library.

libvgm (by Valley Bell) is a modular rewrite of most components from
VGMPlay. It provides four static libraries:

  - vgm-utils  — data loaders (File/Memory, on-the-fly gzip inflate),
                 threading/mutex utilities, codepage conversion (iconv)
  - vgm-emu    — sound chip emulation cores (SN76496, YM2612, YM2151,
                 YM2413, OPL*, C140, C352, ES550x, SCSP, ...)
  - vgm-player — file format players: VGM, S98, DRO, GYM (C++)
  - vgm-audio  — audio output library (on OHOS only the WaveWriter
                 file sink is built; no ALSA/PulseAudio on device)

Build system: CMake >= 3.12, languages C + C++14.

Snapshot g20260121 = upstream master commit
57585ea7a53f56bcf5a56071068c6ef9154ca299 (2026-01-21, "simplify list
returned by GetSongDeviceInfo()"). Upstream has no release tags.

External dependencies: zlib (DataLoader gzip support), pthreads,
iconv (musl libc built-in on OHOS), libm. On OHOS the S98 player's
Shift-JIS tag conversion (CP932) is unavailable because musl's iconv
does not implement CP932 — S98Player degrades gracefully (tags stay
unconverted); VGM, the primary format, is unaffected (UTF-16LE works).

License: upstream ships no top-level LICENSE file; components carry
their own licenses (33 MAME BSD-3-Clause cores, Nuked* LGPL/GPL,
Gens YM2612 GPL, Maxim SN76489 public-domain-style, ...). Recorded
as NOASSERTION — see notes.md.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibVgmConan(ConanFile):
    name = "libvgm"
    version = "g20260121"
    description = (
        "Video Game Music playback library (modular VGMPlay rewrite): "
        "VGM/S98/DRO/GYM players + sound chip emulation cores"
    )
    license = "NOASSERTION"  # 上游无顶层 LICENSE，组件混合许可，见 notes.md
    homepage = "https://github.com/ValleyBell/libvgm"
    url = "https://github.com/ValleyBell/libvgm"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: 平台兼容性检查
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libvgm {self.version} only supports Linux and OHOS, "
                f"got os={self.settings.os}"
            )

    def requirements(self):
        # DataLoader 的 gzip 解压路径需要 zlib（vgm-utils 默认启用 UTIL_LOADERS）
        self.requires("zlib/1.3.2")

    def export_sources(self):
        pass  # 无补丁

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 基于 Linux 内核，CMake 不识别 OHOS → 显式声明为 Linux
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # aarch64 小端，跳过 CMake 端序探测
        tc.variables["CMAKE_C_BYTE_ORDER"] = "LITTLE_ENDIAN"
        tc.variables["CMAKE_CXX_BYTE_ORDER"] = "LITTLE_ENDIAN"
        # 上游用 LIBRARY_TYPE 而非标准 BUILD_SHARED_LIBS
        tc.variables["LIBRARY_TYPE"] = "SHARED" if self.options.shared else "STATIC"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # 上游默认 USE_SANITIZERS=ON 会注入 -fsanitize=*, OHOS 关闭
        tc.variables["USE_SANITIZERS"] = False
        # 只构建库本体：测试程序是交互式开发工具，CLI 播放器不随库分发
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_PLAYER"] = False
        tc.variables["BUILD_VGM2WAV"] = False
        # 音频驱动：OHOS 无 ALSA/Pulse/libao/OSS 开发包，仅保留纯文件输出 WaveWriter
        tc.variables["AUDIODRV_ALSA"] = False
        tc.variables["AUDIODRV_PULSE"] = False
        tc.variables["AUDIODRV_LIBAO"] = False
        tc.variables["AUDIODRV_OSS"] = False
        tc.variables["AUDIODRV_SADA"] = False
        tc.variables["AUDIODRV_WAVEWRITE"] = True
        # 子库功能保持默认全开（DataLoader/线程/字符集转换均为播放必需）
        tc.generate()

    def build(self):
        # 上游无 ctest 测试目标（test 程序为交互式开发工具，需手动准备
        # VGM 测试数据），故 build 阶段不调用 cmake.test()；
        # 消费者级验证见 test_package（PlayerA 渲染最小 VGM 断言非静音）。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 静态链接顺序：依赖者在前（vgm-player → vgm-emu/vgm-utils，
        # vgm-audio → vgm-utils）
        self.cpp_info.libs = ["vgm-player", "vgm-audio", "vgm-emu", "vgm-utils"]
        # 头文件安装到 include/vgm/，两种包含拼写均支持：
        #   #include "player/playera.hpp"  或  #include "vgm/player/playera.hpp"
        self.cpp_info.includedirs = ["include/vgm", "include"]
        # 公共头 stdtype.h 依赖 HAVE_STDINT_H（上游 configure 时探测的定义）
        self.cpp_info.defines = ["HAVE_STDINT_H"]
        # vgm-utils 的 DataLoader 静态链接时传递 zlib
        self.cpp_info.requires = ["zlib::zlib"]
        self.cpp_info.set_property("cmake_target_name", "libvgm::libvgm")
        self.cpp_info.set_property("pkg_config_name", "libvgm")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]
