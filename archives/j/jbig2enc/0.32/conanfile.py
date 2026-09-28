#!/usr/bin/env python3
"""Conan recipe — jbig2enc 0.32 (Autotools, C++).

JBIG2 图像编码器（encoder 方向，jbig2dec 的对偶件）：libjbig2enc 静态库 +
jbig2 命令行工具。上游 https://github.com/agl/jbig2enc tag 0.32 是 git archive
（无 configure），build() 先 autoreconf -fi 自举（abiword-plugin 系同法）。

依赖（configure.ac 实证，仅 2 项）：
  - AC_CHECK_LIB(leptonica, findFileFormatStream)  → leptonica/1.85.0（硬依赖）
  - PKG_CHECK_MODULES(LEPTONICA, lept >= 1.74)     → 同上（pkg-config 探测）
  - AC_CHECK_LIB(m, sqrt)                          → 系统库
  （configure.ac 全文无 lcms/webp/png/jpeg/tiff 直连——subprojects/*.wrap 只是
   上游 meson 子项目 wrapdb 镜像清单，与 autotools 构建无关，不引依赖）

OHOS 适配要点：
  1. git archive 无 configure：build_requirements 拉 automake/1.18 +
     libtool/2.5.4 + pkgconf/3.0.5（tool_requires，abiword-plugin-clarisworks
     同法）。pkgconf 双重用途：提供 pkg.m4（PKG_CHECK_MODULES 宏，aclocal 需）
     + pkgconf 可执行文件（PKG_CONFIG 探测）。
  2. 上游 0.32 的 config.guess（timestamp 2023-08-22）原生识别 HarmonyOS →
     aarch64-unknown-linux-ohos，config.sub 原生接受该 triplet，零补丁。
     但 configure 的编译探针仍需显式 --host/--build（交叉编译标准姿势）。
  3. configure 生成文件 umask 077 在 HMDFS 上产生 drwx--S--- 不可写临时目录
     → autoreconf 后对 configure 做 umask 077→022 替换（E011/E114 类，
     liburcu 0003/coinutils 同款；abiword 用函数替换，此处用 patch 固化）。
  4. leptonica 探测三件套（generate()）：
     - PkgConfigDeps：生成 lept.pc 及全部依赖 pc（configure 的
       PKG_CHECK_MODULES 命中）
     - AutotoolsDeps：CPPFLAGS/LDFLAGS/lib（AC_CHECK_LIB 的 -lleptonica 命中）
     - AutotoolsToolchain：CC/CXX/--host/--build
     PKG_CONFIG_PATH 指到 generators 目录。
  5. 交叉编译探针运行：configure 编译的 conftest 链接了 leptonica 的 .so，
     运行时需 LD_LIBRARY_PATH 含依赖 libdir（LDFLAGS -L 集合回填，从
     conanautotoolsdeps 的 LDFLAGS 提取）。
  6. make -j1（E074：HMDFS jobserver fifo EPERM）。

上游测试（rule4 如实申报）：
  上游 jbig2enc 0.32 无测试框架（无 tests/ 目录、Makefile.am 无 TESTS、
  无 make check 目标、.github/workflows 仅 Ruff Python lint + 三平台构建
  矩阵，无测试步骤）→ N=0 如实申报。
  兜底（clancyxie 口径）：test_package 消费者测试——用 jbig2 工具对合成
  PNG 真实编码（generic + symbol 两种模式），断言 JB2 魔数头 + 输出非空 +
  symbol 模式产出 .sym 符号表（R34：实质调用被测包二进制与 API）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """hnp/automake 安装的 aclocal/automake 硬编码了本环境不存在的绝对
    路径（@am_AUTOM4TE@ / autoconf）。把 env vars 指向 PATH 上实际可用的
    工具（abiword-plugin-clarisworks 同款）。"""
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


class Jbig2EncConan(ConanFile):
    name = "jbig2enc"
    version = "0.32"
    description = "JBIG2 image encoder (library + jbig2 CLI tool), the encoder-side twin of jbig2dec"
    license = "Apache-2.0"
    homepage = "https://github.com/agl/jbig2enc"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        pass  # 无补丁（umask 修复是 autoreconf 后的运行时替换）

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jbig2enc is only supported on Linux/OHOS, not " + str(self.settings.os))

    def requirements(self):
        # configure.ac 唯一三方依赖：leptonica >= 1.74（AC_CHECK_LIB +
        # PKG_CHECK_MODULES 双探测）。1.85.0 是制品仓带完整格式链的版本
        # （zlib/png/jpeg/gif/tiff/openjpeg 六件套，mupdf/tesseract 同源）。
        self.requires("leptonica/1.85.0")

    def build_requirements(self):
        # git archive 无 configure：autoreconf -fi 自举需要 automake/libtool；
        # PKG_CHECK_MODULES 宏需要 pkg.m4（pkgconf 提供）；configure 的
        # PKG_CONFIG 探测需要 pkg-config 兼容可执行文件（pkgconf 提供）。
        # CI 预检容器只有 autoconf 套件（abiword-plugin-clarisworks 同法）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        # git archive 无 configure——umask 补丁打在 autoreconf 生成的 configure
        # 上（build() 里 autoreconf 之后 apply，此处只解源码）
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        # PkgConfigDeps：lept.pc + 依赖链 pc 文件（PKG_CHECK_MODULES 命中）
        pcdeps = PkgConfigDeps(self)
        pcdeps.generate()
        # AutotoolsDeps：CPPFLAGS/LDFLAGS（AC_CHECK_LIB 的 -lleptonica 命中）
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # 上游 0.32 的 config.guess 原生识别 HarmonyOS，但交叉编译仍需显式
        # triplet（configure 编译探针不能跑在 build 机上）
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # R26: 非 libjbig2enc 非系统同名库，但编码器工具链生态以静态为主
        # （jbig2_LDFLAGS=-static 上游默认），保持静态默认
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # autoreconf 自举（git archive 无 configure）。pkg.m4 从 pkgconf
        # tool_requires 拷进 m4/（PKG_CHECK_MODULES 宏，aclocal 自动拾取）
        pkgconf_m4 = self._find_pkgconf_m4()
        if pkgconf_m4:
            m4dir = os.path.join(self.source_folder, "m4")
            os.makedirs(m4dir, exist_ok=True)
            shutil.copy(pkgconf_m4, os.path.join(m4dir, "pkg.m4"))
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E011/E114 类：HMDFS 上 umask 077 创建的 confXXXXXX 临时目录是
        # drwx--S---（setgid 传染 + others 无权限），config.status 子进程
        # 写 subs1.awk 失败。autoreconf 生成的 configure 做运行时文本替换
        # （abiword-plugin-clarisworks _drop_umask_077 同款——不用补丁是因为
        # automake 1.17/1.18 生成的 configure 行号有漂移，补丁 hunk 会 miss）
        self._drop_umask_077(os.path.join(self.source_folder, "configure"))
        # configure 运行环境：
        # - PKG_CONFIG_PATH 指到 PkgConfigDeps 生成目录（PKG_CHECK_MODULES 命中）
        # - LD_LIBRARY_PATH 补齐依赖 libdir（交叉编译探针 conftest 链接
        #   leptonica .so 后要能运行——直接从依赖包遍历提取，不依赖
        #   conanbuild env 的时序）
        from conan.tools.env import Environment
        runenv = Environment()
        runenv.define("PKG_CONFIG_PATH", self.generators_folder)
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
            # E074: HMDFS jobserver fifo EPERM
            autotools.make(args=["-j1"])

    def _drop_umask_077(self, path):
        """E011/E114 类：HMDFS 强制 setgid，`umask 077 && mktemp -d` 产生
        drwx--S--- 临时目录，连属主都不可写。去掉 umask 077（保留括号结构
        以免破坏 shell 语法）。abiword-plugin-clarisworks 同款。"""
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        data = data.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
        data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)

    def _find_pkgconf_m4(self):
        for _, dep in self.dependencies.items():
            if dep.ref.name == "pkgconf":
                cand = os.path.join(dep.package_folder, "share", "aclocal", "pkg.m4")
                if os.path.exists(cand):
                    return cand
        return None

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["jbig2enc"]
        # jbig2 CLI 工具（bin/jbig2 + bin/jbig2topdf.py）由 commands.json 声明
        self.cpp_info.set_property("cmake_file_name", "jbig2enc")
        self.cpp_info.set_property("cmake_target_name", "jbig2enc::jbig2enc")
        self.cpp_info.set_property("pkg_config_name", "jbig2enc")
        # 依赖链传递（下游链接 libjbig2enc 时自动带齐 leptonica 链）
        self.cpp_info.requires = ["leptonica::leptonica"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
