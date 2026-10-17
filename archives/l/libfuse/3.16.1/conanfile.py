#!/usr/bin/env python3
"""Conan recipe — libfuse 3.16.1 (FUSE 3.x, Meson).

libfuse 是 FUSE (Filesystem in Userspace) 的参考实现。OpenHarmony 用户态
不提供 /dev/fuse，无法真正挂载文件系统，因此适配目标是让 lib 本身在
aarch64-linux-ohos 上完整编译、可被下游链接，并把 libc 缺失的 POSIX 线程
取消 API 换成等价实现（有界 poll + 退出标志），而不是空壳 stub。

源码改动见 patches/：meson 侧特性探测 HAVE_PTHREAD_CANCEL，C 侧以
#ifdef/#ifndef 守卫（meson 的 configuration_data 在布尔为真时写出无值
`#define`，因此不能用 `#if HAVE_X`）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibfuseConan(ConanFile):
    name = "libfuse"
    version = "3.16.1"
    description = "Filesystem in Userspace (FUSE) library, version 3"
    license = "LGPL-2.1-or-later AND GPL-2.0-only"
    homepage = "https://github.com/libfuse/libfuse"
    url = "https://github.com/libfuse/libfuse"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # Meson 1.11.0 已发布到制品仓（先例：c-list/3.1.0、account-utils/1.4.0）
        self.tool_requires("meson/1.11.0")

    def validate(self):
        # R32: 平台判断必须用 in ("Linux", "OHOS") 形式，不能 == "Linux"
        if self.settings.os not in ("Linux", "FreeBSD", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports Linux, FreeBSD and OHOS only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: 与系统同名的库默认静态，避免污染设备的 /lib
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # 只打包库本体：util 需要 /etc/mtab 与 udev 规则，example 与 test 都需要
        # 真正挂载 FUSE 文件系统（OHOS 无 /dev/fuse），上游 meson 唯一注册的
        # wrong_command 用例本身设计为返回 1（提示改用 pytest），故不启用 tests。
        tc.project_options["utils"] = False
        tc.project_options["examples"] = False
        tc.project_options["tests"] = False
        tc.project_options["useroot"] = False
        # CI worker 的 PATH 不保证含 llvm-ar/llvm-ranlib，而 Meson 在 project()
        # 阶段就要探测归档器；从 profile 的 compiler_executables 推导同目录工具
        # 写入 machine file 的 [binaries]（先例：c-list/3.1.0、atk/2.38.0.1.1）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if cc:
            tool_dir = os.path.dirname(cc)
            tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["fuse3"]
        # 上游安装 lib/pkgconfig/fuse3.pc
        self.cpp_info.set_property("pkg_config_name", "fuse3")
        if self.settings.os in ("Linux", "FreeBSD"):
            # OHOS 的 libc 已内建 pthread/dl/rt，无需额外系统库
            self.cpp_info.system_libs = ["pthread", "dl", "rt"]
