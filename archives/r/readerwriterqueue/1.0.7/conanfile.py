#!/usr/bin/env python3
"""Conan recipe — readerwriterqueue 1.0.7 (header-only)

moodycamel 单头文件 SPSC 队列库：无编译产物，仅安装头文件到 include/。
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import cmake_layout


class ReaderwriterqueueConan(ConanFile):
    name = "readerwriterqueue"
    version = "1.0.7"
    description = "A fast single-producer, single-consumer lock-free queue (header-only)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/cameron314/readerwriterqueue"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def configure(self):
        # R32 平台检测：header-only 库理论平台无关，仍遵守规程做白名单校验。
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "readerwriterqueue 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        apply_conandata_patches(self)
        # header-only：无编译步骤
        pass

    def package(self):
        # 上游 CMakeLists.txt 将头文件安装到 include/readerwriterqueue/
        for hdr in ("readerwriterqueue.h", "readerwritercircularbuffer.h", "atomicops.h"):
            copy(
                self,
                hdr,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "include", "readerwriterqueue"),
            )
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
