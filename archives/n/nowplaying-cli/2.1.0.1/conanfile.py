#!/usr/bin/env python3
"""Conan recipe — nowplaying-cli 2.1.0.1 (OpenHarmony AVSession equivalent port).

Pure C++17 CMake CLI. The only external dependency is the OHOS native
AVSessionKit (libohavsession.so), which ships with the OHOS native SDK under
<sysroot>/usr/lib/aarch64-linux-ohos — no Conan requires are needed.

Upstream nowplaying-cli (kirtan-shah/nowplaying-cli) is macOS-only
(Foundation/AppKit/MediaRemote private framework) and cannot build on OHOS
(no libobjc/libdispatch/Foundation). This package is the pure C/C++ OHOS
equivalent port built against the native AVSession provider API; see
README.md "API gap" for the controller-side limitation.

Version note (R37): upstream 2.1.0 already occupied in the archive tree, so
this equivalent port carries the fix suffix .1 → 2.1.0.1.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class NowplayingcliConan(ConanFile):
    name = "nowplaying-cli"
    version = "2.1.0.1"
    description = "nowplaying-cli OpenHarmony equivalent port (AVSession provider CLI)"
    license = "MIT"
    homepage = "https://github.com/kirtan-shah/nowplaying-cli"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Equivalent port: no upstream OHOS source exists (upstream is macOS-only
    # ObjC). The C++ source tree is bundled directly via exports_sources so
    # that CI can build without any external URL download.
    exports_sources = "CMakeLists.txt", "src/*", "README.md"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external Conan deps: the only linkage is the OHOS system SDK
        # library libohavsession.so (AVSessionKit), resolved via the
        # OHOS sysroot at build time.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Source is bundled via exports_sources — no external download needed.
        # If conandata has sources (from a build cache), it will be used
        # automatically; otherwise exports_sources provides the files.
        if self.conan_data.get("sources", {}).get("url", ""):
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS native SDK ships libohavsession.so in the sysroot; conan's
        # CMakeToolchain already points at the OHOS toolchain via the
        # ohos-aarch64 profile. Nothing else is required.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # CLI tool: executable goes to bin/. bindirs is the Conan declaration
        # consumed by `conan create` + consumers (`conan install` puts the
        # binary on PATH through virtualrunenv).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
