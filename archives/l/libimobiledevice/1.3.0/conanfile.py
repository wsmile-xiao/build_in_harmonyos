#!/usr/bin/env python3
"""Conan recipe — libimobiledevice 1.3.0 (Autotools).

libimobiledevice 生态：iOS 设备通信库（libimobiledevice-1.0）。
ideviceinstaller 依赖链：libusbmuxd → libimobiledevice → ideviceinstaller。

构建要点：
  - autotools（configure.ac 依赖 libusbmuxd-2.0 >= 2.0.2 + libplist-2.0 >= 2.2.0）
  - SSL 后端：openssl（registry 有 openssl/1.1.1w；gnutls/libtasn1 OHOS 无，
    用 --enable-openssl 强制 openssl 后端）
  - PkgConfigDeps 生成 libusbmuxd.pc/libplist.pc/openssl.pc，
    PKG_CONFIG_PATH 指向 generators
  - AutotoolsToolchain 不导出 CC（ccd2iso 教训），显式注入 CC/CXX 绝对路径
"""
import os

import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibimobiledeviceConan(ConanFile):
    name = "libimobiledevice"
    version = "1.3.0"
    description = "Library to communicate with iOS devices (libimobiledevice ecosystem)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libimobiledevice/libimobiledevice"
    url = "https://github.com/libimobiledevice/libimobiledevice"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusbmuxd/2.0.2")
        self.requires("libplist/2.3.0")
        # SSL 后端：openssl（OHOS 无 gnutls/libtasn1）
        self.requires("openssl/1.1.1w")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
        # causing config.status to fail writing subs*.awk. Create a mktemp wrapper
        # that returns failure to force autoconf AS_TMPDIR to use mkdir fallback.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("conanbuild")
    def generate(self):
        # 依赖包（libplist/libusbmuxd）安装的 .la 文件 libdir='//lib' 无效
        # （conan autotools 安装 prefix 处理缺陷），libtool 链接时递归解析
        # .la 报 "not a valid libtool archive"。将依赖包 lib 下 *.la 改名，
        # libtool 找不到 .la 时直接链接 .a（静态链接，符号完整）。
        import glob as _glob
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                for la in _glob.glob(os.path.join(dep.package_folder, libdir, "*.la")):
                    os.rename(la, la + ".bak")

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-openssl")
        # config.guess 不识别 OHOS（libplist 先例）
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()
        PkgConfigDeps(self).generate()
        env = Environment()
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        env.define("CC", compilers.get("c", "clang"))
        env.define("CXX", compilers.get("cpp", "clang++"))
        env.vars(self).save_script("conanbuild_env")

    def build(self):
        # OHOS 沙箱 umask 077 + mktemp -d 生成 0700 目录，config.status 写
        # subs*.awk Permission denied（librrd/ccd2iso 先例）：patch umask 022
        conf = os.path.join(self.source_folder, "configure")
        replace_in_file(self, conf, "umask 077", "umask 022")

        apply = Autotools(self)
        apply.configure()
        apply.make(args=["-j1"])

    def package(self):
        apply = Autotools(self)
        apply.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["imobiledevice-1.0"]
        self.cpp_info.set_property("pkg_config_name", "libimobiledevice-1.0")
