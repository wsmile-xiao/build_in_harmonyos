#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""libinklevel 0.9.7 —— HarmonyOS PC (OHOS / aarch64) 适配配方

上游用 autotools 构建，configure 通过 pkg-config 探测 libusb-1.0 与 libxml-2.0，
两者在制品仓均已发布为 Conan 包，按 R36 直接依赖，不做捎带适配。

适配要点：
  * patches/0001-bjnp-debug.c.patch
    bjnp-debug.c 的 helper 定义被 `#ifndef NDEBUG` 包住而调用点无守卫，Release
    (-DNDEBUG) 下共享库残留未解析符号，消费者加载即失败；去守卫常编译修复。
  * patches/0002-config.guess.patch、patches/0003-config.sub.patch
    上游 2009 年的 libtool 三元组不认识 OHOS，按 E007 补 aarch64-*-linux-ohos。
  * patches/0004-configure.patch
    configure 的 `mktemp -d ./confXXXXXX` 临时目录分支在 HMDFS（E490）上不可用，
    改为固定目录名。
  * generate() 用 PkgConfigDeps 生成 libusb-1.0.pc / libxml-2.0.pc，AutotoolsToolchain
    会把 generators 目录挂进 PKG_CONFIG_PATH；依赖路径全部落在 Conan 构建目录内，
    不写共享 /usr/local（R49）。
"""

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

import os


class LibinklevelConan(ConanFile):
    name = "libinklevel"
    version = "0.9.7"
    description = ("libinklevel reads the ink level of inkjet printers "
                   "(Canon, Epson, HP) over USB, parallel port or BJNP network protocol")
    license = "GPL-2.0"
    homepage = "https://libinklevel.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")
        self.requires("libxml2/2.15.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # .la 记录构建期绝对路径，删除以免污染消费者的 libtool 链路
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libinklevel")
        self.cpp_info.set_property("cmake_target_name", "libinklevel::libinklevel")
        self.cpp_info.set_property("pkg_config_name", "libinklevel")
        self.cpp_info.libs = ["inklevel"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
