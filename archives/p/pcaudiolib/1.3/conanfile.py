#!/usr/bin/env python3
"""Conan recipe — pcaudiolib 1.3 (portable C audio library for espeak-ng).

pcaudiolib 是 espeak-ng 使用的便携 C 音频库：跨平台音频输出（PulseAudio/
ALSA/OSS/Cygwin），提供统一的 audio.open/close/play 抽象。autotools 构建，
无硬依赖（PulseAudio/ALSA 为可选 --with-* 后端，OHOS 无音频设备可关闭）。

OHOS 适配：
- 沿用 main 已收录的 0001-config-ohos.patch：config.guess/config.sub 加
  HarmonyOS 分支（aarch64-unknown-linux-ohos），否则交叉编译
  "unable to guess system type"。
- 关闭可选音频后端（--without-pulseaudio --without-alsa --without-oss
  --without-cygwin）——OHOS 无音频设备。
- E114：config.status/configure 的 umask 077 临时目录 HMDFS 拒绝 →
  改写 umask 022（与 asterisk/speech-dispatcher 同款）。
"""
import os
import re as _re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PcaudiolibConan(ConanFile):
    name = "pcaudiolib"
    version = "1.3"
    package_type = "library"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/espeak-ng/pcaudiolib"
    description = "pcaudiolib — portable C audio library for espeak-ng"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pcaudiolib does not support os={self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=x86_64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            # 关闭可选音频后端（OHOS 无音频设备）
            "--without-pulseaudio", "--without-alsa", "--without-oss",
            "--without-cygwin",
            # rpl_malloc：交叉编译下 AC_FUNC_MALLOC 无法实测 malloc(0)，
            # 显式置 yes（musl malloc(0) 正常）
            "ac_cv_func_malloc_0_nonnull=yes",
            "ac_cv_func_realloc_0_nonnull=yes",
        ])
        # 源码 src/audio_priv.h 等 `#include <pcaudiolib/audio.h>`，而顶层
        # Makefile.am 的 `AM_CFLAGS = -Isrc/include` 是相对路径——out-of-tree
        # 构建（conan build-release 目录）下解析到 build 目录而非源码目录，
        # 报 "pcaudiolib/audio.h' file not found"。显式补绝对源码 include 路径。
        tc.cflags.append("-I%s/src/include" % self.source_folder)
        tc.generate()

    def _patch_umask_077(self):
        """E114：config.status/configure 用 `umask 077 && mktemp -d ./confXXXXXX`
        创建 0700 临时目录——HMDFS 拒绝该权限（Permission denied）。改写为
        umask 022（与 asterisk/speech-dispatcher 同款）。
        """
        import glob as _glob
        targets = [os.path.join(self.source_folder, "config.status"),
                   os.path.join(self.source_folder, "configure")]
        targets += _glob.glob(os.path.join(self.source_folder, "**",
                                           "config.status"), recursive=True)
        for path in targets:
            if not os.path.isfile(path):
                continue
            data = open(path, encoding="utf-8", errors="replace").read()
            if "umask 077" not in data:
                continue
            data = data.replace("umask 077 && mktemp -d", "umask 022 && mktemp -d")
            data = data.replace("(umask 077 && mkdir", "(umask 022 && mkdir -p")
            open(path, "w", encoding="utf-8", newline="\n").write(data)
            self.output.info(f"pcaudiolib: patched umask 077→022 in {path}")

    def _patch_include_path(self):
        """顶层 Makefile.am 用 `AM_CFLAGS = -Isrc/include`（相对路径）——out-of-tree
        构建（conan build-release 目录）下 `-Isrc/include` 解析到 build 目录而非
        源码目录，src/audio_priv.h 的 `#include <pcaudiolib/audio.h>` 报 not found。
        改 Makefile.in 为 `-I$(top_srcdir)/src/include`（configure 输入，非 .am——
        改 .am 会触发 make 重跑 automake）。
        """
        path = os.path.join(self.source_folder, "Makefile.in")
        if not os.path.isfile(path):
            return
        data = open(path, encoding="utf-8", errors="replace").read()
        if "$(top_srcdir)/src/include" in data:
            return
        data = data.replace("-Isrc/include", "-I$(top_srcdir)/src/include")
        open(path, "w", encoding="utf-8", newline="\n").write(data)
        self.output.info("pcaudiolib: patched Makefile.in -Isrc/include → "
                         "$(top_srcdir)/src/include")

    def build(self):
        apply_conandata_patches(self)
        self._patch_umask_077()
        self._patch_include_path()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # ── 上游测试（rule 4 实测回填）──
        # pcaudiolib 无独立测试套件（configure.ac 无 check_PROGRAMS/TESTS，
        # 顶层无 test/ 目录）——按 rule 1.2 如实声明；make check 尝试执行。
        self.run("make check", env="conanbuild", ignore_errors=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # CI（#79xx）：OHOS 拒绝加载未签名 .so——test_package 的 dlopen
        # 报 "Permission denied"。与 cairo-gobject 同款：用 OHOS 的
        # binary-sign-tool 对打包的共享库自签名（先移除旧 .codesign 段）。
        # 不依赖 settings.os 判定（CI 的 os 设置可能不同导致签名未执行），
        # 改为：工具存在即签名，工具缺失则跳过（方法内 guard）。
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        import glob as _glob
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.info("pcaudiolib: binary-sign-tool not found, skip signing")
            return
        targets = _glob.glob(os.path.join(self.package_folder, "lib", "**",
                                          "*.so"), recursive=True)
        targets += _glob.glob(os.path.join(self.package_folder, "lib", "**",
                                           "*.so.*"), recursive=True)
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{target}" '
                     f'2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{target}" -outFile "{target}" '
                     f'-selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["pcaudiolib"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
