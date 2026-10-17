#!/usr/bin/env python3
"""Conan recipe for vgmplay 0.52.0 — command-line VGM player (libvgm-based).

VGMPlay (by Valley Bell) is the official command-line player for Video Game
Music files (VGM/VGZ, S98, DRO, GYM). This packaging targets the
``vgmplay-libvgm`` repository release 0.52.0, which links against libvgm
(the modular VGMPlay rewrite) rather than bundling its own emulation cores.

Build system: CMake >= 3.6, languages C + C++ (uses getopt_long, runs on a
terminal; on OHOS it is validated purely through its non-interactive CLI).

Upstream source tarball notes:
  - ``libvgm``, ``libs/inih`` and ``libs/wingetopt`` are git submodules and are
    NOT present in the GitHub archive tarball. We provide libvgm and inih as
    Conan dependencies (find_package CONFIG); wingetopt is MSVC-only and not
    needed on OHOS.
  - The upstream CMake links four per-sub-library CMake targets
    (libvgm::vgm-utils / vgm-audio / vgm-emu / vgm-player) exported by the
    libvgm *submodule* build. The Conan libvgm package exports a single
    aggregate target libvgm::libvgm. Patch 0001 adapts both the inih detection
    and the target names.

Dependencies:
  - libvgm/g20260121   (Conan, ohpcd published) — emulation + playback engine
  - inih/r58           (Conan, ohpcd published) — INI config parser
  - zlib, pthread, m, iconv — pulled transitively via libvgm
  - Media Controls (D-Bus on Linux) disabled on OHOS (MEDIA_CONTROLS=OFF);
    no ALSA/Pulse audio device is required for the non-interactive smoke test.

License: vgmplay itself is GPL-2.0-or-later; it links libvgm (NOASSERTION,
mixed component licenses). Recorded as GPL-2.0-or-later for the player app.
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class VgmplayConan(ConanFile):
    name = "vgmplay"
    version = "0.52.0"
    description = (
        "Command-line VGM (Video Game Music) player, libvgm-based "
        "(VGM/VGZ, S98, DRO, GYM)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ValleyBell/vgmplay-libvgm"
    url = "https://github.com/ValleyBell/vgmplay-libvgm"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: 平台兼容性检查
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"vgmplay {self.version} only supports Linux and OHOS, "
                f"got os={self.settings.os}"
            )

    def requirements(self):
        # libvgm 提供声音芯片模拟 + VGM/S98/DRO/GYM 播放引擎
        self.requires("libvgm/g20260121")
        # INI 配置解析（上游 bundled inih 是 submodule，archive 中缺失）
        self.requires("inih/r58")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # OHOS 基于 Linux 内核，CMake 不识别 OHOS → 显式声明为 Linux
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # aarch64 小端，跳过 CMake 端序探测
        tc.variables["CMAKE_C_BYTE_ORDER"] = "LITTLE_ENDIAN"
        tc.variables["CMAKE_CXX_BYTE_ORDER"] = "LITTLE_ENDIAN"
        # 媒体控制：OHOS 无 D-Bus 开发包，显式关闭（上游 UNIX 分支会 QUIET
        # 探测 DBus1，找不到则 OFF；这里显式给值保证构建确定性）
        tc.variables["MEDIA_CONTROLS"] = "OFF"
        # playctrl.cpp 的 WAV dump 路径直接调用 WavWrt_SetFileName，该声明在
        # libvgm 的 audio/AudioStream_SpcDrvFuns.h 中被 #ifdef AUDDRV_WAVEWRITE
        # 包住。OHOS 上 libvgm 仅构建 WaveWriter 驱动，需定义此宏以暴露声明。
        tc.preprocessor_definitions["AUDDRV_WAVEWRITE"] = "1"
        # OHOS 内核要求用户态 ELF 携带代码签名段才能 execve，否则报
        # "Operation not permitted" (exit 126)。链接时加 -Wl,--code-sign
        # （与仓库既有写法一致；clang wrapper 亦会自动注入，此处显式声明
        # 保证不依赖 wrapper 行为）。
        tc.extra_ldflags = ["-Wl,--code-sign"]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # 上游无 ctest/make check 测试目标（vgmplay 是交互式播放器，
        # --help/--version/--lib-info 是非交互自检入口，验证见 test_package）
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # 不能用 cmake.install()：CMake install 时会清除/改写 RUNPATH，
        # 这会破坏 OHOS --code-sign 嵌入的代码签名段，导致内核拒绝 execve
        # （"Operation not permitted", exit 126）。直接逐文件复制，保持 ELF 原样。
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "vgmplay", src=self.build_folder, dst=bin_dir)
        # 数据文件（上游 PLAYER_EXTRA_INSTALL），Unix 上转小写名
        for src_name, dst_name in [
            ("Updates.txt", "updates.txt"),
            ("VGMPlay.ini", "vgmplay.ini"),
            ("VGMPlay.txt", "vgmplay.txt"),
        ]:
            copy(self, src_name, src=self.source_folder, dst=bin_dir, keep_path=False)
            src = os.path.join(bin_dir, src_name)
            dst = os.path.join(bin_dir, dst_name)
            if os.path.exists(src):
                os.rename(src, dst)

    def package_info(self):
        # 命令行工具：把 bin/ 加入运行 PATH（consumers 可直接调用 vgmplay）
        self.cpp_info.bindirs = ["bin"]
