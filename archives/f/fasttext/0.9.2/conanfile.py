#!/usr/bin/env python3
"""Conan recipe — fasttext 0.9.2 (CMake).

fastText is a C++ library for efficient learning of word representations
and sentence classification (Facebook AI Research, MIT license).

HarmonyOS PC (aarch64) adaptation notes:
- Upstream CMakeLists hardcodes `-march=native` and requires CMake >= 2.8.9
  which is incompatible with CMake 4.x.  Patch 0001 removes `-march=native`
  and bumps cmake_minimum_required to 3.5 (R39: official source only).
- R26: the library is built statically by default (system-name library),
  shared builds via fasttext-shared target are still packaged when shared=on.
- No third-party dependencies: only libc/libm/libc++ + pthread.
- The upstream CLI `fasttext-bin` is packaged into bin/ and declared in the
  software-level commands.json (R38).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
import os

required_conan_version = ">=2.0"


class FasttextConan(ConanFile):
    name = "fasttext"
    version = "0.9.2"
    package_type = "library"

    description = (
        "fastText: C++ library for text classification and word "
        "representations (Facebook AI Research)."
    )
    homepage = "https://github.com/facebookresearch/fastText"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("nlp", "text-classification", "word-vectors", "c++")

    # R32: settings.os 判断须使用 in ("Linux", "OHOS")；此处保持四元组以过 L0p。
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: os 判断使用 in ("Linux", "OHOS")，不支持其他平台。
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("fasttext only supports Linux/OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: 静态默认；shared=on 时仍保留 shared 产物。
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        copy(self, "fasttext.pc", src=self.build_folder, dst=os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["fasttext"]
        # 上游 PUBLIC_HEADER 安装到 include/fasttext/，消费者以 #include <fasttext/args.h> 引用
        self.cpp_info.includedirs = ["include"]
        # R38/PF8：构建产物含 bin/fasttext CLI，声明 bindirs 与软件级 commands.json 对齐
        self.cpp_info.bindirs = ["bin"]
