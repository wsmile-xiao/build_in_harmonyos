#!/usr/bin/env python3
"""Conan recipe — libusbmuxd 2.0.2 (Autotools).

libimobiledevice 生态：iOS 设备 USB multiplexing 库（libusbmuxd-2.0）。
ideviceinstaller 依赖链：libusbmuxd → libimobiledevice → ideviceinstaller。

构建要点：
  - autotools（configure.ac 依赖 libplist-2.0 >= 2.2.0，registry 有 libplist/2.3.0）
  - PkgConfigDeps 生成 libplist.pc，PKG_CONFIG_PATH 指向 generators
  - AutotoolsToolchain 不导出 CC（ccd2iso 教训），显式注入 CC/CXX 绝对路径
"""
import os

import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibusbmuxdConan(ConanFile):
    name = "libusbmuxd"
    version = "2.0.2"
    description = "iOS device USB multiplexing library (libimobiledevice ecosystem)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libimobiledevice/libusbmuxd"
    url = "https://github.com/libimobiledevice/libusbmuxd"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        self.requires("libplist/2.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

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
        tc = AutotoolsToolchain(self)
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
        self.cpp_info.libs = ["usbmuxd-2.0"]
        self.cpp_info.set_property("pkg_config_name", "libusbmuxd-2.0")
