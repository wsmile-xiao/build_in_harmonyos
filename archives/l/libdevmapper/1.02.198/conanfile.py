#!/usr/bin/env python3
"""Conan recipe — libdevmapper 1.02.198 (LVM2 源码树内的 device-mapper 用户态库组件).

上游没有独立 libdevmapper 归档：本包从官方 LVM2 2.03.24 源码树构建 device-mapper
组件（libdm/），产物为 libdevmapper.so + libdevmapper.h，可被 `-ldevmapper`
链接（父库 cryptmount 6.4.0 通过 AC_CHECK_HEADER + AC_SEARCH_LIBS(dm_task_create, devmapper)
无条件消费）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdevmapperConan(ConanFile):
    name = "libdevmapper"
    version = "1.02.198"
    description = "device-mapper userspace library (libdevmapper) from LVM2 2.03.24"
    license = "LGPL-2.1"
    homepage = "https://sourceware.org/lvm2/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # LVM2 的递归 make（libdm/tools/daemons）在 conan 默认 out-of-source
        # build 目录下会因 VPATH/getcwd 异常产出空 libdm——强制 in-source 构建，
        # 与手动验证成功的构建路径一致。三个目录统一为 "." 使
        # AutotoolsToolchain.generate() 与 Autotools() 读取同一 conanbuild.conf。
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 名义三元组用 -linux-gnu 后缀配合 build() 中的 uname-shim，让 autotools/config.sub
        # 按 Linux-ELF 处理；真实交叉目标由 profile 的 CC/CXX（OHOS clang）决定。
        _arch_triplet = {"armv8": "aarch64-linux-gnu", "x86_64": "x86_64-linux-gnu"}
        arch = str(self.settings.arch)
        triplet = _arch_triplet.get(arch)
        if triplet is None:
            raise ConanInvalidConfiguration(
                f"libdevmapper 1.02.198 配方目标为 HarmonyOS PC，仅支持 armv8/x86_64，收到 arch='{arch}'"
            )
        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--host={triplet}")
        tc.configure_args.append(f"--build={triplet}")
        # DESTDIR 安装布局：--prefix=/ + package() 中 DESTDIR={package_folder}
        # → 产物直接落在 include/ lib/ bin/ 等标准布局。
        tc.configure_args.append("--prefix=/")
        # 仅构建 device-mapper 组件，禁用 LVM2 其余子系统（守护进程/锁/udev 等）
        tc.configure_args.append("--disable-udev_sync")
        tc.configure_args.append("--disable-selinux")
        tc.configure_args.append("--disable-lvmlockd")
        tc.configure_args.append("--disable-lvmpolld")
        tc.configure_args.append("--disable-dmeventd")
        tc.configure_args.append("--disable-cmirrord")
        tc.configure_args.append("--disable-cmdlib")
        tc.configure_args.append("--disable-blkid_wiping")
        tc.configure_args.append("--disable-thin_check_needs_check")
        tc.configure_args.append("--disable-cache_check_needs_check")
        # 注意：LVM2 不识别 --enable-static/--disable-shared（configure 会告警并忽略），
        # 库构建由 LIB_SUFFIX 决定；本包默认共享 .so（消费者契约仅需 -ldevmapper 可链接，
        # 且 OHOS sysroot 无同名系统库，R26 静态化不适用）。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: 恢复 autotools 脚本可执行位（下载/解压后可能被 strip）。
        for _s in ("configure", "autoconf/config.guess", "autoconf/config.sub",
                   "autoconf/install-sh", "autoconf/missing"):
            _p = os.path.join(self.source_folder, _s)
            if os.path.exists(_p):
                os.chmod(_p, 0o755)
        # HMDFS 共享文件系统：configure/config.status 用 umask 077 建 0700 临时目录，
        # 在共享目录下对非属主进程不可写（Permission denied）。改为 022 与共享目录一致。
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        # config.sub 未知系统判断时返回 OHOS 风格的系统名（uname shim）
        _shim = os.path.join(self.build_folder, '_uname_shim')
        os.makedirs(_shim, exist_ok=True)
        _u = os.path.join(_shim, 'uname')
        with open(_u, 'w') as _f:
            _f.write('#!/bin/sh\ncase "${1:-}" in\n  -s|"") echo Linux ;;\n  -r) echo 6.6 ;;\n  -m) echo aarch64 ;;\n  *) exec /system/bin/uname "$@" 2>/dev/null || exec /bin/uname "$@" ;;\nesac\n')
        os.chmod(_u, 0o755)
        os.environ['PATH'] = _shim + os.pathsep + os.environ.get('PATH', '')
        autotools = Autotools(self)
        autotools.configure()
        # 只构建 device-mapper 组件（libdevmapper.so + dmsetup/dmstats），
        # 不构建 LVM2 完整 lib/ 树（其 bcache.c 无条件 include libaio.h，OHOS sysroot 无此头，
        # 且本包消费者契约仅需要 libdevmapper）。
        autotools.make(args=["-j1", "device-mapper"])

    def package(self):
        # 使用 LVM2 的 install_device-mapper 目标：只安装 device-mapper 组件
        # （libdevmapper.h + libdevmapper.so + dmsetup/dmstats + man），避开全量
        # `make install` 对 lib/ 树（libaio 依赖）的构建。
        self.run(f"make install_device-mapper DESTDIR={self.package_folder}")

    def package_info(self):
        # 消费者契约：AC_SEARCH_LIBS(dm_task_create, devmapper) → -ldevmapper
        self.cpp_info.libs = ["devmapper"]
        # cmake/pkg-config 元数据与包名一致（test_package 用 find_package(libdevmapper)）
        self.cpp_info.set_property("cmake_file_name", "libdevmapper")
        self.cpp_info.set_property("cmake_target_name", "libdevmapper::libdevmapper")
        self.cpp_info.set_property("pkg_config_name", "libdevmapper")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
