#!/usr/bin/env python3
"""Conan recipe for FFTResampler 2.8 — audio FFT resampler CLI tool (C, CMake).

Builds the official upstream source (commit 0a9720bc05105ccf11764be0d22721238306c793,
no formal tag/release upstream) which produces the `FFTResampler` executable
(wav/mp3 -> wav resampler). Single-entry CLI tool, no library artifacts.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FFTResamplerConan(ConanFile):
    name = "fftresampler"
    version = "2.8"
    description = "FFTResampler — simple and efficient FFT-based audio resampler CLI"
    license = "MIT"
    homepage = "https://github.com/cpuimage/FFTResampler"
    url = ""  # CI fills this

    package_type = "application"

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
        tc = CMakeToolchain(self)
        # Upstream declares cmake_minimum_required(VERSION 2.8); modern CMake
        # (>=3.5 baseline) rejects that, so pin the policy floor instead of
        # patching the upstream file (minimal, reversible).
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # cmake_minimum_required(2.8) is evaluated before the toolchain file
        # loads, so CMAKE_POLICY_VERSION_MINIMUM must also be passed on the
        # configure command line to avoid the hard compatibility error.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        # Upstream CMakeLists.txt has no install() rule; copy the built binary.
        copy(self, "FFTResampler", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]