#!/usr/bin/env python3
"""Conan recipe for digitemp 3.7.2 (Makefile) on HarmonyOS PC."""
# digitemp 3.7.2 — OpenHarmony PC (aarch64) 适配配方
# 上游: https://github.com/bcl/digitemp
# 构建系统: 上游自带 Makefile (目标: ds9097 / ds9097u / ds2490)
# 说明: ds2490 (USB 适配器) 上游标注 BROKEN 且依赖 libusb, 本包只构建
#       DS9097 / DS9097U 两种串口适配器版本
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os
import shlex
import shutil


required_conan_version = ">=2.0"


class DigitempConan(ConanFile):
    name = "digitemp"
    version = "3.7.2"
    description = "1-Wire 温度传感器读取工具 (DS9097 / DS9097U 串口适配器)"
    license = "GPL-2.0-or-later"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    homepage = "https://github.com/bcl/digitemp"
    topics = ("1-wire", "temperature", "sensor", "serial", "ds9097")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器一律取自 Conan 工具链配置, 不使用 ${CC} 等未定义的 shell 变量
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        make = shutil.which("make") or "make"
        # ds2490 目标上游标注 BROKEN (需 libusb), 仅构建两种串口适配器版本
        for target in ("ds9097", "ds9097u"):
            self.run(f"{make} CC={shlex.quote(cc)} {target}", cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "digitemp"))
        copy(self, "ChangeLog", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "digitemp"))
        copy(self, "digitemp.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        for binary in ("digitemp_DS9097", "digitemp_DS9097U"):
            copy(self, binary, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"))
            os.chmod(os.path.join(self.package_folder, "bin", binary), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
