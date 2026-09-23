#!/usr/bin/env python3
"""Conan recipe — ee 3.2.2 (custom clang build).

STM32 EEPROM emulation library（NimaLTD.I-CUBE-EE）。
上游为无构建系统的单文件 C 库（copy-into-project 风格），依赖 STM32 HAL
（main.h / HAL_FLASH_*）。本配方通过 patches 注入 OHOS 宿主模拟 HAL
（main.h + ee_sim_flash.c：固定低地址 mmap 模拟 Flash 擦除/编程/直接寻址
读取语义），然后直接以 OHOS 工具链 clang 编译并 llvm-ar 归档。
参考 archives/m/micro-ecc 的同一范式。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EeConan(ConanFile):
    name = "ee"
    version = "3.2.2"
    description = "EEPROM emulation library for STM32 (NimaLTD.I-CUBE-EE)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/nimaltd/ee"
    url = "https://github.com/nimaltd/ee"
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
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        cflags = "-fPIC -O2 -std=c11"
        if self.options.shared:
            self.run(
                f"{cc} {cflags} -I. -c ee.c -o ee.o",
                cwd=self.source_folder,
            )
            self.run(
                f"{cc} {cflags} -I. -c ee_sim_flash.c -o ee_sim_flash.o",
                cwd=self.source_folder,
            )
            self.run(
                f"{cc} -shared ee.o ee_sim_flash.o -o libee.so",
                cwd=self.source_folder,
            )
        else:
            self.run(
                f"{cc} {cflags} -I. -c ee.c -o ee.o",
                cwd=self.source_folder,
            )
            self.run(
                f"{cc} {cflags} -I. -c ee_sim_flash.c -o ee_sim_flash.o",
                cwd=self.source_folder,
            )
            self.run(f"{ar} rcs libee.a ee.o ee_sim_flash.o", cwd=self.source_folder)

    def package(self):
        copy(self, "ee.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "NimaLTD.I-CUBE-EE_conf.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "main.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libee.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libee.so", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE.TXT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ee"]
        # 模拟 HAL 依赖 POSIX mmap，头文件为标准 C/系统头，无需额外包含目录
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = []