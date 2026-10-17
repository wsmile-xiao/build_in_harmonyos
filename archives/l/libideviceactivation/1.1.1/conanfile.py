#!/usr/bin/env python3
"""Conan recipe — libideviceactivation 1.1.1 (Autotools).

libideviceactivation 提供 iOS 设备激活/去激活能力（库 `libideviceactivation-1.0`，
LGPL-2.1+）与命令行工具 `ideviceactivation`（GPL-3.0+）。
上游：https://github.com/libimobiledevice/libideviceactivation

上游强制第三方依赖（configure.ac L39-L42 `PKG_CHECK_MODULES`，四行均**未**提供
action-if-not-found，任一缺失即 configure 硬失败）：
    libimobiledevice-1.0 >= 1.3.0
    libplist-2.0        >= 2.2.0
    libcurl             >= 7.20
    libxml-2.0          >= 2.9
其中 libcurl/libxml2 虽只出现在 `libideviceactivation-1.0.pc` 的 Requires.private，
但 `src/activation.c` 直接 `#include <curl/curl.h>`、`<libxml/parser.h>` 并调用其
API（curl_easy_perform / xmlXPathEvalExpression），且 `src/Makefile.am` 无条件把它们
并入 AM_CFLAGS/AM_LDFLAGS → 动/静态形态下均为**强制直接依赖**，不可裁减。
上游零可选依赖：configure.ac 无任何 AC_ARG_ENABLE/AC_ARG_WITH。

OHOS 适配（三处均为构建期 shim，不改上游源码，故 patches 为空）：

1) `--build=aarch64-unknown-linux-gnu`（config.guess 兜底）
   上游 config.guess 时间戳 2018-03-08，不认识 HarmonyOS：
       $ ./config.guess            → rc=1
       "unable to guess system type" ... uname -s = HarmonyOS
                                     uname -r = HongMeng Kernel 1.12.0
   不显式给出 --build 时 configure 在 "checking build system type" 处失败。
   本机构建与 CI worker 均为 OHOS aarch64，属原生构建，故不传 --host/--target
   （上游 config.sub 同样不识别 `ohos` 三元组，传了反而报
   "Invalid configuration `aarch64-linux-ohos': system `ohos' not recognized"）。

2) mktemp wrapper（HMDFS 临时目录权限，E114 同族）
   HMDFS 上 `umask 077 && mktemp -d` 生成 mode 2700 (drwx--S---) 目录，**属主亦不可写**：
       $ (umask 077; D=$(mktemp -d ./confXXXXXX); touch "$D/subs1.awk")
       touch: './confXXXXXX/subs1.awk': Permission denied
   而 `umask 077 && mkdir` 被 HMDFS 归一为 mode 2771 (drwxrws--x)，可写。
   config.status 用前者建临时目录并写 subs1.awk，于是报：
       ./config.status: line 878: ./confXXXXXX/subs1.awk: Permission denied
       config.status: error: could not setup config files machinery
   让 mktemp 恒定失败即可迫使 autoconf / config.status 走 `(umask 077 && mkdir)` 回退
   分支（config.status L848-L855）。同族先例：libplist / libusbmuxd /
   libimobiledevice-glue / libimobiledevice 均使用同一 wrapper。

3) 依赖包 `.la` 中和（libtool 递归解析陷阱）
   依赖以 `--prefix=/` 发布，`.la` 内 `libdir` 烘焙为 `//lib`，`dependency_libs`
   还含构建机绝对路径（`/storage/.../conan2/p/...`）→ libtool 报：
       libtool: error: '//lib/libplist-2.0.la' is not a valid libtool archive
   本库用 libtool 构建（`AC_PROG_LIBTOOL` + `lib_LTLIBRARIES`），link 时优先解析
   `.la`。build() 开头把各依赖 `lib/*.la` 改名 `*.la.bak`，使 libtool 回退到
   `-L<dir> -l<name>` 解析真实 `.a`。同族先例：ideviceinstaller/1.2.0。
   仅改 conan 缓存副本，不改依赖包配方源码（避免影响其已发布包）。

验证与证据目录（本地跑通记录）：
    .libideviceactivation/logs/10_first_error_configure.log   # 首个错误
    .libideviceactivation/logs/13_probe_tmpdir_perms.log      # HMDFS 权限实测
    .libideviceactivation/logs/15_first_make.log              # libtool .la 错误
    .libideviceactivation/logs/16_fix3_make.log               # 修复后 make 通过
    .libideviceactivation/logs/22_make_check.log              # 上游测试入口实测
    .libideviceactivation/logs/23_upstream_cli_all_commands.log
"""
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibideviceactivationConan(ConanFile):
    name = "libideviceactivation"
    version = "1.1.1"
    description = "Library and tool to activate and deactivate iOS devices (libideviceactivation-1.0)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libimobiledevice/libideviceactivation"
    url = "https://github.com/libimobiledevice/libideviceactivation"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须覆盖 ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libideviceactivation is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # configure.ac L39-L42：四个 PKG_CHECK_MODULES 均无 fallback → 全部强制。
        # transitive_headers=True：本包公共头 libideviceactivation.h 直接包含
        #   <plist/plist.h> 与 <libimobiledevice/lockdown.h>，消费者编译自己的
        #   代码时必须能拿到这两个依赖的 include 目录（conan 默认只把直接依赖的
        #   头文件暴露给消费者，传递依赖的头会被裁掉 → CMakeDeps 生成
        #   <dep>_INCLUDE_DIRS 为空、test_package 编译报 plist/plist.h not found）。
        # transitive_libs=True：libcurl/libxml2 符号出现在本库实现中，静态链接型
        #   消费者需要它们的链接信息。
        self.requires("libimobiledevice/1.3.0", transitive_headers=True, transitive_libs=True)
        self.requires("libplist/2.3.0", transitive_headers=True, transitive_libs=True)
        self.requires("libcurl/8.5.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # ── OHOS-2: mktemp wrapper（HMDFS 上 `umask 077 && mktemp -d` → mode 2700 不可写）
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS/HMDFS: `umask 077 && mktemp -d` creates mode 2700 (drwx--S---)\n'
            '# directories that are not writable even by their owner, so config.status\n'
            '# fails writing subs*.awk.  exit 1 forces autoconf/config.status onto the\n'
            '# `umask 077 && mkdir` fallback (HMDFS normalises it to 2771, writable).\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        # ── OHOS-1: config.guess(2018-03-08) 不识别 HarmonyOS → 显式 --build
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

        # configure.ac 用 PKG_CHECK_MODULES 探测依赖 → 必须由 PkgConfigDeps 提供 .pc
        # （系统 pkg-config 默认 pc_path 指向不存在的 /home/lycium++/... ，sysroot 也无
        #   curl/libxml2 开发文件，故不存在系统同名 .pc 竞争）
        PkgConfigDeps(self).generate()

        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        env.define("CC", compilers.get("c", "clang"))
        env.define("CXX", compilers.get("cpp", "clang++"))
        env.vars(self).save_script("conanbuild_env")

    def build(self):
        # ── OHOS-3: 中和依赖包 .la（libdir='//lib' 烘焙失效，libtool 报 not a valid libtool archive）
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            for libdir in dep.cpp_info.libdirs:
                lib_dir = Path(dep.package_folder) / libdir
                if not lib_dir.is_dir():
                    continue
                for la in lib_dir.glob("*.la"):
                    la.rename(la.parent / (la.name + ".bak"))

        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # R9: 单作业 —— 并行 make 在 HMDFS 上触发 jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=Path(self.package_folder) / "licenses")

    def package_info(self):
        # 上游 pkg-config 名 = libideviceactivation-1.0（src/libideviceactivation-1.0.pc.in）
        self.cpp_info.set_property("pkg_config_name", "libideviceactivation-1.0")
        self.cpp_info.libs = ["ideviceactivation-1.0"]
        # 公共头 libideviceactivation.h 直接包含 <plist/plist.h> 与
        # <libimobiledevice/lockdown.h>，且 activation.c 调用 curl/xml API
        # → 四个上游依赖必须对消费者透传（否则 CMakeDeps 只暴露本包 include）。
        self.cpp_info.requires = [
            "libimobiledevice::libimobiledevice",
            "libplist::libplist",
            "libcurl::libcurl",
            "libxml2::libxml2",
        ]
        # 本包同时产出命令行工具 bin/ideviceactivation（软件级 commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
