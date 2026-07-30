#!/usr/bin/env python3
"""Conan recipe — sound-touch homebrew (upstream 2.4.1)

Audio processing library for changing Tempo, Pitch and Playback Rates.
Homebrew formula version: https://github.com/Homebrew/homebrew-core/blob/master/Formula/s/sound-touch.rb
Homepage: https://www.surina.net/soundtouch/
License: LGPL-2.1-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class SoundTouchConan(ConanFile):
    name = "sound-touch"
    version = "homebrew"
    description = "SoundTouch is an open-source audio processing library for changing the Tempo, Pitch and Playback Rates of audio streams or audio files"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.surina.net/soundtouch/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "neon": [True, False],
    }
    default_options = {
        "neon": False,
    }

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 先尝试主 URL，失败后用 mirror_url 降级（应对 codeberg.org 429 限流）
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as e:
            if mirror_url:
                self.output.warning(f"Primary source failed ({e}), trying mirror: {mirror_url}")
                get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)
            else:
                raise

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable NEON optimizations for OHOS aarch64 compatibility (E099)
        tc.variables["NEON"] = self.options.neon
        # 链接 clang_rt.builtins 解决 __powidf2 符号问题 (E098)
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-lclang_rt.builtins"
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-lclang_rt.builtins"
        tc.generate()

    def build(self):
        # Apply patches (soundtouch_config.h for CMake compat)
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Also copy license file
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["SoundTouch"]
        self.cpp_info.set_property("pkg_config_name", "soundtouch")