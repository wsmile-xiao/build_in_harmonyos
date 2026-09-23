#!/usr/bin/env python3
"""Conan recipe — argp-standalone 1.4.1 (ericonr fork, autotools).

argp-standalone 是 glibc argp(3) 命令行解析接口的独立实现。
OHOS 的 musl libc **不提供 argp**（glibc 专属 API），大量 GNU 软件
（coreutils 系、elfutils、gnulib 类）依赖它 —— 本包补齐 musl/OHOS 的
argp 缺口，静态库 libargp.a + 单一公开头 argp.h。

适配要点（继承 1.5.0 历史经验 + 本次 1.4.1 实测）：
  1. GitHub archive tarball 只含 configure.ac，须 autoreconf 自举；
     设备缺 automake/aclocal，故 tool_requires automake + libtool
     （autoconf 由 automake 依赖链带入）。
  2. musl 的 libintl.h 是空壳（头在、符号不在）：configure 探测到头就
     定义 HAVE_LIBINTL_H，argp-help.c 走 __dcgettext 分支 —— 该符号是
     glibc 内部符号，musl 没有 → 隐式声明 + 链接失败。
     正解：ac_cv_header_libintl_h=no 让其走 dgettext(msgid) 直通分支。
  3. configure/config.status 内嵌 umask 077：HMDFS 上 mktemp -d 出的
     目录缺组执行位（hmmac 强制 g+x 才允许写入），导致 config.status
     "Permission denied" —— umask 022 后可写。修补必须在 autoreconf
     之后做（自举会重新生成 configure）。
  4. 上游 Makefile.am 全是 noinst_* 目标（设计为被内嵌编译），
     make install 什么都不装 → package() 手工装 argp.h + libargp.a
     （与 Alpine APKBUILD 同法）。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ArgpStandaloneConan(ConanFile):
    name = "argp-standalone"
    version = "1.4.1"
    description = "Standalone implementation of the glibc argp command-line argument parser (for libcs without argp, e.g. musl/OHOS)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/ericonr/argp-standalone"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # 源码只有 configure.ac（GitHub archive 不含 configure 生成物），
        # 必须 autoreconf 自举；设备/CI 无系统 automake/aclocal，故显式引入。
        # tool_requires 按 *build profile* 解析，create 时 -pr:h 与 -pr:b 都要给全。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        # 零运行时依赖：musl 提供 getopt/strndup/strchrnul/mempcpy 等全部所需符号
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        # OHOS musl 的 libintl.h 是空壳：头在、__dcgettext 符号不在。
        # 置 HAVE_LIBINTL_H=假 → argp-help.c 走 #define dgettext(d,m) (m) 直通分支。
        # 不能用 -Wno-int-conversion 糊：压住编译告警，链接期照样缺符号。
        # 本包禁 NLS，无需 gettext。
        tc.configure_args.append("ac_cv_header_libintl_h=no")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub archive tarball 从不含 configure（autoreconf 产物不进版本库），
        # 无则自举。判在运行期：同一配方对发布 tarball（自带 configure）也适用。
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
        # ⚠️ configure 内嵌 "umask 077 && mktemp -d"：HMDFS 上 umask 077 建出的
        # 临时目录缺组执行位（hmmac=genfs 要求 g+x 才允许写入），config.status
        # 写 subs1.awk 直接 Permission denied。改为 umask 022 可写。
        # 该修补必须在 autoreconf 之后（自举会重新生成 configure，先改=白改）。
        for _cfg in glob.glob(os.path.join(self.source_folder, "configure")):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
                self.output.info("configure: umask 077 -> 022（HMDFS mktemp 兼容）")
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        # 上游 Makefile.am: noinst_LIBRARIES = libargp.a / noinst_HEADERS = argp.h ...
        # 故意不装任何东西（设计为被别的项目内嵌编译），make install 是空操作。
        # 手工拷（Alpine APKBUILD 同法）：仅装公开头 argp.h（另两个头为内部实现细节）。
        inc = os.path.join(self.package_folder, "include")
        lib = os.path.join(self.package_folder, "lib")
        os.makedirs(inc, exist_ok=True)
        os.makedirs(lib, exist_ok=True)
        header = os.path.join(self.source_folder, "argp.h")
        if not os.path.isfile(header):
            raise Exception("源码树里找不到 argp.h：" + header)
        shutil.copy2(header, os.path.join(inc, "argp.h"))
        found = glob.glob(os.path.join(self.build_folder, "**", "libargp.a"), recursive=True)
        if not found:
            raise Exception("构建产物里找不到 libargp.a")
        shutil.copy2(found[0], os.path.join(lib, "libargp.a"))
        self.output.info("已手工安装 argp.h 与 libargp.a（上游是 noinst，不自带 install）")

    def package_info(self):
        self.cpp_info.libs = ["argp"]
        self.cpp_info.set_property("cmake_file_name", "argp-standalone")
        self.cpp_info.set_property("cmake_target_name", "argp-standalone::argp-standalone")
