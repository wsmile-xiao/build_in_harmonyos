#!/usr/bin/env python3
"""Conan recipe — libspandsp 3.1.1 (Autotools, C).

SpanDSP：软传真/电话 DSP 库（T.30/T.38 传真、V.xx 调制解调器、G.711/
G.722/G.726/GSM0610/LPC10 编解码、DTMF/MFC/R2、回声消除等）。
任务名 libspandsp（平台任务 #13882，taskBranch=feat/libspandsp-3.1.1），
与 main 已有 archives/s/spandsp/0.0.6（旧版 2008 tarball，含预生成
configure）为同一上游——3.1.1 是 GitHub tag v3.1.1 的 git archive，
**无预生成 configure**，走 autoreconf -fi 自举（jbig2enc E6404 同法）。

依赖（configure.ac 实证）：
  - AC_CHECK_LIB(tiff, TIFFOpen) → libtiff/4.7.2（硬依赖，AC_MSG_ERROR）
  - AC_CHECK_LIB(jpeg, jpeg_start_compress) → libjpeg-turbo/3.2.0（硬依赖，
    AC_MSG_ERROR）
  - AC_CHECK_LIB(m, ...) → 系统库
  （--enable-tests 才会查 sndfile/fftw/xml2/pcap/X11/fltk——打包不启用）

OHOS 适配要点：
  1. git archive 无 configure 且 config/ 为空（只有 .empty）：
     tool_requires automake/1.18 + libtool/2.5.4 + pkgconf/3.0.5，
     autoreconf -fi 自举（automake --add-missing 自动安装新版
     config.guess/config.sub，新版原生识别 aarch64-unknown-linux-ohos，
     无需 0.0.6 时代的 config.guess/config.sub 补丁）。
  2. 交叉编译三件套（generate()）：AutotoolsDeps（AC_CHECK_LIB 的
     -ltiff/-ljpeg 命中）+ AutotoolsToolchain（CC/--host/--build）。
  3. E011/E114 类：HMDFS 上 configure umask 077 生成 drwx--S--- 临时目录
     → autoreconf 后对 configure 做运行时文本替换（jbig2enc 同款）。
  4. make -j1（E074：HMDFS jobserver fifo EPERM）；install 也 -j1
     （HMDFS 并行 install-sh -d 建目录竞态，spandsp 0.0.6 同款）。
  5. src/Makefile.am 的生成表工具（make_modem_filter 等 13 个）用
     CC_FOR_BUILD 编译为宿主二进制在构建期运行——交叉编译时
     CC_FOR_BUILD 必须指向宿主 clang（configure.ac 的 Canadian cross
     分支已设 CC_FOR_BUILD=${CC_FOR_BUILD-gcc}，通过环境变量注入宿主
     编译器路径，注意这不是 target clang）。

上游测试（rule4 如实申报口径）：
  上游 tests/ 目录 87 个测试二进制（85 常规 + v32bis/v34 条件 2），
  noinst_PROGRAMS 手工运行形态（无 automake TESTS harness，上游 CI
  build-dispatch.yml 只构建不跑测试）。--enable-tests 需要
  sox/pbmtog3/fax2tiff 外部工具 + libsndfile/fftw/libxml2/libpcap/
  X11/fltk 全家桶（configure 硬失败 AC_MSG_ERROR）——CI 与本机均无，
  属环境限制。可运行子集（纯算法、仅依赖 libspandsp 自身）单独编译
  执行，实测计数见 notes.md；test_package 消费者测试兜底（R34 真断言）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """hnp/automake 安装的 aclocal/automake 硬编码了本环境不存在的
    绝对路径（@am_AUTOM4TE@ / autoconf）。把 env vars 指向 PATH 上实际
    可用的工具（jbig2enc / abiword-plugin-clarisworks 同款）。"""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("aclocal", "ACLOCAL"),
                      ("automake", "AUTOMAKE"),
                      ("libtoolize", "LIBTOOLIZE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


class LibSpanDSPConan(ConanFile):
    name = "libspandsp"
    version = "3.1.1"
    description = "A library of DSP functions for telephony (FAX T.30/T.38, V.xx modems, G.711/G.722/G.726 codecs, DTMF, echo cancel)"
    license = "LGPL-2.1-only"
    homepage = "https://github.com/freeswitch/spandsp"
    url = "https://github.com/freeswitch/spandsp"

    package_type = "library"
    languages = "C"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        pass  # 无补丁（umask 修复是 autoreconf 后的运行时替换）

    def build_requirements(self):
        # git archive 无 configure：autoreconf -fi 自举（E6404 同法）
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("pkgconf/3.0.5")

    def requirements(self):
        # configure.ac 硬依赖：TIFFOpen（libtiff）+ jpeg_start_compress（libjpeg）
        self.requires("libtiff/4.7.2")
        self.requires("libjpeg-turbo/3.2.0")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libspandsp is only supported on Linux/OHOS, not " + str(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # 上游 config.guess（autoreconf --add-missing 安装的新版）原生识别
        # HarmonyOS，但交叉编译仍需显式 triplet（configure 编译探针不能跑
        # 在 build 机上）
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # R26: 非系统同名库，但 telephony 生态以静态链接为主（0.0.6 先例同款）
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 不构建 doc/tests（tests 需 sox/netpbm/fltk/X11 全家桶，环境无）
        tc.configure_args.append("--disable-doc")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # pkg.m4 从 pkgconf tool_requires 拷进 m4/（aclocal 自动拾取）
        pkgconf_m4 = self._find_pkgconf_m4()
        if pkgconf_m4:
            m4dir = os.path.join(self.source_folder, "m4")
            os.makedirs(m4dir, exist_ok=True)
            shutil.copy(pkgconf_m4, os.path.join(m4dir, "pkg.m4"))
        # autoreconf 自举（git archive 无 configure）。注意：新 m4 的
        # pkg.m4 与上游仓库可能自带的版本冲突时以 tool_requires 版本为准
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E011/E114：HMDFS umask 077 临时目录修复（jbig2enc 同款运行时替换）
        self._drop_umask_077(os.path.join(self.source_folder, "configure"))
        # 运行环境：交叉编译探针 conftest 链接 tiff/jpeg .so 后要能运行
        runenv = Environment()
        libdirs = []
        for _, dep in self.dependencies.items():
            if dep.package_folder:
                for ld in dep.cpp_info.aggregated_components().libdirs:
                    ld = os.path.normpath(ld)
                    if ld and os.path.isdir(ld) and ld not in libdirs:
                        libdirs.append(ld)
        if libdirs:
            add = ":".join(libdirs)
            old = os.environ.get("LD_LIBRARY_PATH", "")
            runenv.define("LD_LIBRARY_PATH", add + (":" + old if old else ""))
        autotools = Autotools(self)
        with runenv.vars(self).apply():
            autotools.configure()
            # configure.ac 在 build==host 分支硬设 CC_FOR_BUILD="\$(CC)"——
            # 命令行/环境变量均被覆盖。生成表工具（make_v34_probe_signals
            # 等 13 个）include spandsp.h → tiffio.h，必须带依赖 include；
            # 对生成的 src/Makefile 做运行时替换（_drop_umask_077 同款模式）
            self._fix_cc_for_build(os.path.join(self.build_folder, "src", "Makefile"))
            # E074: HMDFS jobserver fifo EPERM → -j1
            autotools.make(args=["-j1"])

    def _drop_umask_077(self, path):
        """E011/E114 类：HMDFS 强制 setgid，`umask 077 && mktemp -d` 产生
        drwx--S--- 临时目录，连属主都不可写。去掉 umask 077（保留括号结构
        以免破坏 shell 语法）。jbig2enc / abiword-plugin 同款。"""
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        data = data.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
        data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)

    def _fix_cc_for_build(self, makefile_path):
        """configure.ac 在 build==host 分支把 CC_FOR_BUILD 硬设为 "\$(CC)"，
        覆盖命令行/环境变量传递。src/Makefile 的 13 个生成表工具规则
        （make_modem_filter/make_v34_probe_signals 等）不带 $(CPPFLAGS)，
        而 spandsp.h 包含 tiffio.h 与 <spandsp/telephony.h> → 必须给
        CC_FOR_BUILD 注入依赖 include 路径 + 源码树 src/（上游开发时
        srcdir==builddir，分离构建时 <spandsp/*.h> 只在源码树）。
        对生成的 Makefile 做运行时替换（_drop_umask_077 同款模式）。"""
        if not os.path.isfile(makefile_path):
            return
        incdirs = []
        # 源码树 src/（<spandsp/*.h> 头文件子目录所在）与 tools/
        # （meteor-engine.h——make_v34_tx_pre_emphasis_filters 的 FIR 设计
        # 引擎）；上游开发时 srcdir==builddir，分离构建时只在源码树
        for sub in ("src", "tools"):
            d = os.path.join(self.source_folder, sub)
            if os.path.isdir(d):
                incdirs.append(os.path.normpath(d))
        for _, dep in self.dependencies.items():
            if dep.package_folder:
                for idir in dep.cpp_info.aggregated_components().includedirs:
                    idir = os.path.normpath(idir)
                    if idir and os.path.isdir(idir) and idir not in incdirs:
                        incdirs.append(idir)
        if not incdirs:
            return
        cc_build = "/data/service/hnp/bin/clang " + " ".join(f"-I{d}" for d in incdirs)
        with open(makefile_path, "r", encoding="utf-8") as f:
            data = f.read()
        old = "CC_FOR_BUILD = $(CC)"
        if old in data:
            data = data.replace(old, f"CC_FOR_BUILD = {cc_build}")
            with open(makefile_path, "w", encoding="utf-8") as f:
                f.write(data)

    def _find_pkgconf_m4(self):
        for _, dep in self.dependencies.items():
            if dep.ref.name == "pkgconf":
                cand = os.path.join(dep.package_folder, "share", "aclocal", "pkg.m4")
                if os.path.exists(cand):
                    return cand
        return None

    def package(self):
        # -j1: HMDFS 并行 install-sh -d 建目录竞态（0.0.6 先例同款）
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = ["spandsp"]
        self.cpp_info.set_property("cmake_file_name", "spandsp")
        self.cpp_info.set_property("cmake_target_name", "spandsp::spandsp")
        self.cpp_info.set_property("pkg_config_name", "spandsp")
        # 依赖链传递（下游链接 libspandsp 时自动带齐 tiff/jpeg 链）
        self.cpp_info.requires = ["libtiff::libtiff", "libjpeg-turbo::libjpeg-turbo"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
