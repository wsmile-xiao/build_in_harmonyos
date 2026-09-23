#!/usr/bin/env python3
"""Conan recipe — ideviceinstaller 1.2.0 (Autotools).

iOS 设备应用安装/卸载/管理 CLI 工具（依赖 libimobiledevice 生态）。
依赖链：libusbmuxd → libimobiledevice → ideviceinstaller。

构建要点：
  - autotools（configure.ac 依赖 libimobiledevice-1.0 >= 1.3.0 +
    libplist-2.0 >= 2.3.0 + libzip >= 0.10）
  - PkgConfigDeps 生成 libimobiledevice.pc/libplist.pc/libzip.pc，
    PKG_CONFIG_PATH 指向 generators
  - AutotoolsToolchain 不导出 CC（ccd2iso 教训），显式注入 CC/CXX 绝对路径
  - CLI 工具：package_type=application，需 commands.json（R38，软件级目录）
  - 消费者侧禁用依赖包 libtool *.la 包装：依赖包以 --prefix=/ 发布，
    .la 内 libdir 烘焙为 //lib，CI worker 上 libtool 优先解析 .la 报
    "cannot find the library '//lib/libplist-2.0.la'"（.so 实际在 conan
    包 lib/ 下，-L 正常可见）。build() 开头将各依赖 lib/*.la 改名
    *.la.bak 使 libtool 回退到 -L + -l 解析真实 .so。仅消费者侧处理，
    不改依赖包配方（避免影响其已发布包与其他 PR）。
"""
import os

from pathlib import Path

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class IdeviceinstallerConan(ConanFile):
    name = "ideviceinstaller"
    version = "1.2.0"
    description = "Tool to manage apps on iOS devices (install/uninstall/list)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/libimobiledevice/ideviceinstaller"
    url = "https://github.com/libimobiledevice/ideviceinstaller"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("libimobiledevice/1.3.0")
        self.requires("libplist/2.3.0")
        self.requires("libzip/1.11.4")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS aarch64 交叉编译：
        # --host 告知 configure 目标平台（config.sub 需识别 ohos，0001 补丁已处理）
        # --build 告知构建系统类型（跳过 config.guess 探测——OHOS 沙箱下
        #   config.guess 写临时文件会 Permission denied 导致 configure 失败）
        tc.configure_args.extend([
            "--host=aarch64-unknown-linux-ohos",
            "--build=aarch64-unknown-linux-gnu",
            "ac_cv_func_malloc_0_nonnull=yes",
            "ac_cv_func_realloc_0_nonnull=yes",
        ])
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
        # 消费者侧禁用依赖包 libtool *.la 包装（见模块 docstring）：
        # 依赖包以 --prefix=/ 发布，.la 内 libdir 烘焙为 //lib，CI worker
        # 上 libtool 优先解析 .la 报 "cannot find the library
        # '//lib/libplist-2.0.la'"。改名 *.la.bak 使 libtool 回退到 -L +
        # -l 解析 conan 包 lib/ 下真实 .so。仅改 conan 包目录（缓存副本），
        # 不改依赖包配方源码。
        # 遍历全部（含传递依赖，如 libusbmuxd）——libusbmuxd 的 .la
        # dependency_libs 烘焙了 /lib/*.la 绝对路径，同样是解析源
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            dep_lib = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for entry in os.listdir(dep_lib):
                if entry.endswith(".la"):
                    os.rename(os.path.join(dep_lib, entry),
                              os.path.join(dep_lib, entry + ".bak"))

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
        self.cpp_info.bindirs = ["bin"]
