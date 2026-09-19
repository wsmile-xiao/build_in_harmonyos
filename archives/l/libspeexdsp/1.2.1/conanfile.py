#!/usr/bin/env python3
"""Conan recipe — libspeexdsp (Audio processing library for Speex codec).

Xiph Speex DSP 处理库（重采样/AEC/降噪/自动增益）。包名 libspeexdsp 与既有归档
speexdsp/*（1.2.1）不同——同 libvorbis/vorbis、libogg/ogg、libopus/opus 的多包名
并存先例（Debian/上游生态习惯命名 libspeexdsp1/libspeexdsp-dev）。
Build system: Autotools (configure + make)，零外部依赖。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibSpeexdspConan(ConanFile):
    name = "libspeexdsp"
    version = "1.2.1"
    description = "Audio processing library for Speex codec (AEC, denoising, resampling)"
    license = "BSD-3-Clause"
    homepage = "https://speex.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Fix mktemp issue in configure script (E002: /tmp read-only on OHOS)
        # config.status uses mktemp -d "./confXXXXXX" which creates dirs in CWD,
        # but HMDFS doesn't allow this on OHOS
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(
                self, configure_path,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp="${TMPDIR:-/tmp}/conan-cs-$$"',
            )

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["speexdsp"]
        self.cpp_info.set_property("pkg_config_name", "speexdsp")
