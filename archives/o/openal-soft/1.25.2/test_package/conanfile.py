#!/usr/bin/env python3
"""Conan test_package — openal-soft 1.25.2

L1 test: verify a consumer can link against OpenAL and exercise the
built-in Null/loopback backends without any real audio device:
- alcOpenDevice("No Output") — null backend
- ALC_SOFT_loopback: alcLoopbackOpenDeviceSOFT + alcCreateContext with
  ALC_FORMAT_CHANNELS_SOFT / ALC_FORMAT_TYPE_SOFT / ALC_FREQUENCY +
  alcRenderSamplesSOFT (960 samples)
- NB: 1.25.2 has no alcSetFormat; loopback format is set via the context
  attribute list.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpenALSoftTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dep = self.dependencies["openal-soft"]
        dep_libdir = os.path.join(dep.package_folder, "lib")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_openal")
        self.run(f'export LD_LIBRARY_PATH="{dep_libdir}:$LD_LIBRARY_PATH"; {bin_path}', env="conanrun")
