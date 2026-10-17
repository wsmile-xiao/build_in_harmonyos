#!/usr/bin/env python3
"""Conan recipe — libltdl 2.6.0 (GNU libtool 运行时动态加载库, autotools).

libltdl 是 GNU libtool 2.6.0（2026-01 alpha, alpha.gnu.org 官方 tarball）
源码树里的 dlopen 封装库（lt_dlinit/lt_dlopen/lt_dlsym/lt_dlexit）。
本配方只打包 libltdl 库 + 头文件，不含 libtoolize/libtool 工具。

要点:
- R26 系统同名库: 默认 shared=False（--disable-shared --enable-static），
  只产出静态库，避免同名动态库污染系统 /lib、/lib64。
- 显式 --host/--build=aarch64-unknown-linux-gnu: config.guess 无法识别
  `uname -s=HarmonyOS`，与历史 libtool 2.5.4.1 同法。
- E011 (HMDFS): 原版 configure 生成的 config.status 用 `umask 077` 建临时目录
  （mktemp -d 0700），HMDFS 把目录 owner 映射为 20001006 而进程 uid 是
  20020101 → 0700 目录不可写 → `config.status: could not setup config files
  machinery`。构建前把 configure 里的 `umask 077` 放宽为 `umask 002`
  （历史 libtool 2.5.4.1 同款处理；本机实测 umask 002 → 目录 2771，组可写）。
- 上游 testsuite 实测通过率（修复后权威数据，见 notes.md 申报表 / reports/
  test-report.md）：harness 设 AUTOM4TE=usr/local/bin/autom4te + mktemp shim（E011,
  HMDFS umask）+ PATH 补 /bin（设备 id 只在 /bin）+ gzip shim（toybox gzip 不认
  --best）后全量跑，185 组 = 142 ok / 8 failed / 35 skipped。8 个 failed 中 5 个为
  上游声明的 expected failure（XFAIL），仅剩 3 个：106 versioning_script（上游
  libtool-next-version 脚本硬编码 uname -s OS 白名单，HarmonyOS 落 *) 分支报 unknown
  OS）、116 lt_dladvise（HarmonyOS 动态链接器不支持跨 dlopen 模块符号解析，RTLD_GLOBAL
  无效——最小独立样例实证）——均为平台硬限制；185 cmdline_wrap（内层重跑含 106 硬限制
  而判失败，非独立失败）。CI 不跑上游 testsuite（conan create
  只做编译验证 + test_package 冒烟），不影响发布。
- 无外部依赖: libltdl.la dependency_libs 为空，dlopen 由系统 libc 提供。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibltdlConan(ConanFile):
    name = "libltdl"
    version = "2.6.0"
    description = "GNU libtool's portable dlopen wrapper library (runtime dynamic loading)"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gnu.org/software/libtool/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 无外部依赖: dlopen 由系统 libc 提供（W0 已核验）
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 显式三元组: config.guess 不认 HarmonyOS（历史 2.5.4.1 已验证法）
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # R26: 系统同名库默认静态
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E011 (HMDFS): config.status 的 `umask 077` 临时目录在 HMDFS 的
        # UID 映射下不可写 → 放宽为 umask 002（历史 2.5.4.1 同法，
        # 对普通 Linux 无副作用：mktemp -d 本身固定 0700 归构建用户所有）。
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"),
                              recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as _f:
                    _txt = _f.read()
            except OSError:
                continue
            if "umask 077" in _txt:
                with open(_cfg, "w", encoding="utf-8") as _f:
                    _f.write(_txt.replace("umask 077", "umask 002"))
                self.output.info("configure umask 077 -> 002: %s" % _cfg)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        try:
            # MAKEINFO=true: 设备/CI 无 texinfo（makeinfo 缺失 → doc/libtool.info
            # Error 127），跳过 info 生成；与历史 libtool 2.5.4.1 同法。
            autotools.install(args=["-j1", "MAKEINFO=true"])
        except Exception as exc:
            # HMFS chmod/hardlink 受限时 libtool `install -c && chmod` 会失败
            # （gmime 3.0.6 同款坑）→ 纯 Python 复制，字节一致、不改权限。
            self.output.warning(f"autotools.install failed ({exc}); "
                                "fallback to pure-Python copy")
            self._fallback_install_python()
        # 只留 libltdl 库 + 头文件: 去掉工具 bin/、宏 share/ 与 .la 元数据
        for sub in ("bin", "sbin", "libexec", "share"):
            d = os.path.join(self.package_folder, sub)
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for f in os.listdir(lib_dir):
                if f.endswith(".la"):
                    try:
                        os.unlink(os.path.join(lib_dir, f))
                    except OSError:
                        pass
        # 自检: 必须存在 lib + 头文件
        self._assert_package_layout()

    def _assert_package_layout(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")
        lib_ok = False
        if os.path.isdir(lib_dir):
            lib_ok = os.path.isfile(os.path.join(lib_dir, "libltdl.a")) or \
                     any(f.startswith("libltdl.") and f.endswith((".a", ".so"))
                         for f in os.listdir(lib_dir))
        if not lib_ok:
            raise Exception("package layout: libltdl.{a,so} missing in " + str(lib_dir))
        if not os.path.isfile(os.path.join(inc_dir, "ltdl.h")):
            raise Exception("package layout: include/ltdl.h missing")

    def _fallback_install_python(self):
        """HMFS chmod/hardlink 受限时的纯 Python 安装（参考 gmime 正例）。"""
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)

        # 1) 静态库 libltdl.a（build 树 .libs 或源码树 .libs）
        candidates = []
        for root, _dirs, files in os.walk(self.build_folder):
            for f in files:
                if f == "libltdl.a":
                    p = os.path.join(root, f)
                    if os.path.isfile(p) and os.path.getsize(p) > 0:
                        candidates.append(p)
        if not candidates:
            for root, _dirs, files in os.walk(self.source_folder):
                if ".libs" in root:
                    for f in files:
                        if f == "libltdl.a":
                            p = os.path.join(root, f)
                            if os.path.isfile(p) and os.path.getsize(p) > 0:
                                candidates.append(p)
        if not candidates:
            raise Exception("fallback install: libltdl.a not found")
        src = max(candidates, key=lambda p: os.path.getsize(p))
        shutil.copy2(src, os.path.join(lib_dir, "libltdl.a"))

        # 2) 共享库（shared=True 时）
        if self.options.shared:
            for root, _dirs, files in os.walk(self.build_folder):
                for f in files:
                    if f.startswith("libltdl.so"):
                        try:
                            shutil.copy2(os.path.join(root, f),
                                         os.path.join(lib_dir, f))
                        except OSError:
                            pass
            # 生成 .so -> .so.7.x 软链
            reals = sorted(f for f in os.listdir(lib_dir)
                           if f.startswith("libltdl.so") and f.count(".") >= 2)
            if reals:
                real = reals[-1]
                for link in ("libltdl.so.7", "libltdl.so"):
                    ln = os.path.join(lib_dir, link)
                    if not os.path.lexists(ln):
                        os.symlink(real, ln)

        # 3) 头文件: include/ltdl.h + include/libltdl/*.h
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dir, exist_ok=True)
        src_top = os.path.join(self.source_folder, "libltdl")
        if os.path.isfile(os.path.join(src_top, "ltdl.h")):
            shutil.copy2(os.path.join(src_top, "ltdl.h"),
                         os.path.join(inc_dir, "ltdl.h"))
        else:  # 生成的头文件可能在 build 树
            for root, _dirs, files in os.walk(self.build_folder):
                if "ltdl.h" in files:
                    shutil.copy2(os.path.join(root, "ltdl.h"),
                                 os.path.join(inc_dir, "ltdl.h"))
                    break
        hdr_src = os.path.join(src_top, "libltdl")
        if os.path.isdir(hdr_src):
            shutil.copytree(hdr_src, os.path.join(inc_dir, "libltdl"),
                            dirs_exist_ok=True)
        try:
            size = os.path.getsize(os.path.join(lib_dir, "libltdl.a"))
        except OSError:
            size = -1
        self.output.info(f"fallback install layout: libltdl.a size={size}")

    def package_info(self):
        self.cpp_info.libs = ["ltdl"]
        self.cpp_info.includedirs = ["include"]
        # 默认 CMake 目标 libltdl::libltdl / find_package(libltdl)
        self.cpp_info.set_property("cmake_file_name", "libltdl")
        self.cpp_info.set_property("cmake_target_name", "libltdl::libltdl")
