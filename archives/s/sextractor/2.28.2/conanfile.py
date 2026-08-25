#!/usr/bin/env python3
"""Conan recipe for sextractor (Source-Extractor) 2.28.2 — FITS source
extraction tool, autotools — AstrOmatic suite.

Dependencies:
  - cfitsio/4.6.4 (FITS I/O)
  - fftw/3.3.10   (FFT)
  - openblas/0.3.34 (BLAS/LAPACK)
  - zlib (cfitsio transitive link)

sextractor is a command-line tool; package contains `sex` and
`ldactoasc` binaries.
"""
import os
import re
import glob as _glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SextractorConan(ConanFile):
    name = "sextractor"
    version = "2.28.2"
    description = "Source-Extractor: FITS image source extraction"
    license = "GPL-3.0-or-later"
    homepage = "https://www.astromatic.net/software/sextractor"
    url = "https://github.com/astromatic/sextractor"
    exports_sources = "conandata.yml", "patches/*"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def build_requirements(self):
        # GitHub archive tarball 无预生成 configure，需 autoreconf 自举
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        self.requires("cfitsio/4.6.4")
        # sextractor 需要单精度 FFTW（libfftw3f——acx_fftw.m4 检查
        # FFTW single precision 实测；fftw/3.3.10 只含双精度）——
        # 用 fftw3f/3.3.9（scamp 同款，已发布 ohpcd）
        self.requires("fftw3f/3.3.9")
        self.requires("openblas/0.3.34")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["sextractor"],
            strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # cross.cache：CI el2 沙箱无法运行 conftest——'C compiler cannot
        # create executables' 实测（#6257 教训：ac_cv_prog_cc_works + 
        # ac_cv_prog_cc_cross 同时预置——只预置 cross 不够——autoconf
        # AC_PROG_CC 先查 works 再查 cross）
        # Autotools 在 build-release/ 子目录跑 configure（out-of-source——
        # configure 命令实测 --cache-file=.../build-release/cross.cache）——
        # cross.cache 必须写到 build-release/（generate 时 build_folder 是
        # 源码目录 b/——写 b/cross.cache 时 configure 读 build-release/ 缓存
        # 未命中实测）——两个位置都写确保命中
        for _cache_dir in (self.build_folder,
                           os.path.join(self.build_folder, "build-release")):
            os.makedirs(_cache_dir, exist_ok=True)
            with open(os.path.join(_cache_dir, "cross.cache"), "w") as f:
                f.write("ac_cv_prog_cc_works=yes\n")
                f.write("ac_cv_prog_cc_cross=yes\n")
        # 不传 --cache-file：Autotools 在 build-release/ 跑 configure 时对
        # cache-file 相对路径再加一层（实测 --cache-file=.../build-release/
        # build-release/cross.cache——双重路径文件不存在）——ac_cv_prog_cc_
        # works/cross 用 configure 命令行 VAR=value 传递（speex 先例）
        # CI worker 沙箱禁止生成/运行 conftest 可执行文件 →
        # 'checking whether the C compiler works... no'（#30633 实测，
        # 同 asterisk-srtp/speex 17 轮 CI 失败根因）——configure 命令行
        # cache 变量 ac_cv_prog_cc_works=yes 强制跳过该运行检查（speex
        # 1.2.1 main 先例——configure VAR=value 等价 cache 变量，比
        # cross.cache 文件可靠——cross.cache 预置 works 在部分 autoconf
        # 版本无效实测）
        tc.configure_args.append("ac_cv_prog_cc_works=yes")
        tc.configure_args.append("ac_cv_prog_cc_cross=yes")
        cfitsio = self.dependencies["cfitsio"]
        fftw = self.dependencies["fftw3f"]
        blas = self.dependencies["openblas"]
        zlib = self.dependencies["zlib"]
        tc.configure_args.extend([
            # 注意：不加 --build（scamp 同款 config.guess patch 已内联
            # 识别 OHOS——CI 上显式 --build 导致 C compiler works 检查
            # 失败实测，同 psfex/weightwatcher/skymaker 三库教训）
            "--with-cfitsio-libdir=%s" % os.path.join(
                cfitsio.package_folder, "lib"),
            "--with-cfitsio-incdir=%s" % os.path.join(
                cfitsio.package_folder, "include"),
            "--with-fftw-libdir=%s" % os.path.join(
                fftw.package_folder, "lib"),
            "--with-fftw-incdir=%s" % os.path.join(
                fftw.package_folder, "include"),
            "--enable-openblas",
            "--with-openblas-libdir=%s" % os.path.join(
                blas.package_folder, "lib"),
            "--with-openblas-incdir=%s" % os.path.join(
                blas.package_folder, "include"),
            # OHOS pthread.h 未声明 pthread_cancel（同 swarp 实测）——
            # 禁用多线程（单线程模式完全可用）
            "--enable-threads=no",
        ])
        # 显式注入 zlib 路径与库（cfitsio.a 的传递依赖——AC_CHECK_LIB
        # 测试链接需要 -L 路径 + -lz，否则 CFITSIO library not found 实测）
        tc.extra_ldflags.append(
            "-L%s" % os.path.join(zlib.package_folder, "lib"))
        tc.extra_ldflags.append("-lz")
        # 编译期头文件注入（configure 的 --with-fftw-incdir 仅检查阶段
        # 生效——make 编译 src/fft.h 时仍需 -I——实测 fftw3.h not found；
        # 同注入 openblas/cfitsio include）
        tc.extra_cflags.append(
            "-I%s" % os.path.join(fftw.package_folder, "include"))
        tc.extra_cflags.append(
            "-I%s" % os.path.join(blas.package_folder, "include"))
        tc.extra_cflags.append(
            "-I%s" % os.path.join(cfitsio.package_folder, "include"))
        tc.generate()

    def _patch_ohos_autotools(self):
        """config.guess/config.sub 内联补 OHOS 识别（同 scamp 先例）。

        注意：sextractor 源码树同时存在 config/（配置文件目录——
        default.conv 等）与 autoconf/（AC_CONFIG_AUX_DIR 指向
        autoconf——config.guess 实际所在）——按目录存在性判断会走错
        分支（同 psfex 实测）——按 config.guess 文件存在性判断。
        """
        for aux in (os.path.join(self.source_folder, "autoconf"),
                    os.path.join(self.source_folder, "config")):
            if os.path.isfile(os.path.join(aux, "config.guess")):
                break
        cg = os.path.join(aux, "config.guess")
        cs = os.path.join(aux, "config.sub")
        if os.path.isfile(cg):
            text = open(cg, encoding="utf-8", errors="ignore").read()
            changed = False
            if "HarmonyOS" not in text:
                block = (
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    "\tesac\n"
                    "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                    "\t;;\n\n")
                new = re.sub(r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)",
                             block + r"\1", text, flags=re.M)
                changed = new != text
                text = new
            if changed:
                open(cg, "w", encoding="utf-8").write(text)
                self.output.info("已修补 config.guess: 加入 HarmonyOS 识别")
        if os.path.isfile(cs):
            text = open(cs, encoding="utf-8", errors="ignore").read()
            changed = False
            if "ohos-linux" not in text:
                pat = re.compile(
                    r"(?P<ind>^\s*)android-linux\)\n"
                    r"(?P<body>(?:\s*basic_machine=\$field1-unknown\n)?"
                    r"\s*basic_os=linux-android\n"
                    r"\s*;;\n)",
                    re.M)
                m = pat.search(text)
                if m:
                    ind = m.group("ind")
                    new = (
                        m.group(0) +
                        ind + "ohos-linux)\n" +
                        ind + "basic_machine=$field1-unknown\n" +
                        ind + "basic_os=linux-ohos\n" +
                        ind + ";;\n")
                    text = text[:m.start()] + new + text[m.end():]
                    changed = True
            if "gnu* | android* | ohos*" not in text:
                new = text.replace("gnu* | android*",
                                   "gnu* | android* | ohos*")
                changed = changed or new != text
                text = new
            if "linux-ohos" not in text:
                new = text.replace("linux-uclibc* )",
                                   "linux-uclibc* | linux-ohos* )")
                new = new.replace("linux-uclibc*- )",
                                  "linux-uclibc*- | linux-ohos*- )")
                changed = changed or new != text
                text = new
            if changed:
                open(cs, "w", encoding="utf-8").write(text)
                self.output.info("已修补 config.sub: 加入 ohos triplet 支持")

    def build(self):
        os.umask(0)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder,
                                           "configure")):
            self.output.info("源码树无 configure（GitHub archive），先 autoreconf")
            autotools.autoreconf()
            self._patch_ohos_autotools()
            # 新 autoconf（automake 1.18 配套）的 works 检查不读
            # ac_cv_prog_cc_works 缓存（ac_cv_prog_cc_works=yes 命令行传入
            # 仍运行 works 检查实测——CI #3079x）——patch configure：
            # works 检查编译测试 if 强制成功（跨编译下 works 检查跳过
            # 合理——cadaver neon patch 同款模式）
            _cfg_ws = os.path.join(self.source_folder, "configure")
            _ws = open(_cfg_ws).read()
            _old_ws = 'if { { ac_try="$ac_link_default"'
            if _old_ws in _ws:
                # 不能把 `if { { ...` 改成 `if true; then`（会破坏 shell
                # 分组语法——`}` 结尾无匹配——syntax error near '}' 实测
                # CI #3079x）——只改 ac_try 命令值（编译测试 → true——
                # 分组结构保留——ac_try 执行 true 成功——works 检查通过）
                _ws = _ws.replace(
                    _old_ws, 'if { { ac_try=true  # [ohos] force works',
                    1)
                open(_cfg_ws, "w").write(_ws)
                self.output.info("configure works check forced (ac_try=true)")
            else:
                self.output.warning("configure works check pattern not found")
        # OHOS: config.status 临时目录 umask 077 → 000（hmdfs 上失败）
        for _cfg in _glob.glob(
                os.path.join(self.source_folder, "**", "configure"),
                recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 000"))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # sex 是命令行工具，无库文件
