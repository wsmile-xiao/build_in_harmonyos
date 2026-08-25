#!/usr/bin/env python3
"""Conan recipe for source-extractor 2.28.2 (SExtractor, autotools).

SExtractor (Source Extractor) extracts sources from astronomical images and
builds object catalogs — the core tool of the AstrOmatic suite (Debian name
source-extractor). Installs the `sex` and `ldactoasc` CLI binaries.

Dependencies (all published on ohpcd):
  - fftw3f/3.3.9.1  (single-precision FFTW; configure ACX_FFTW fflag=yes)
  - openblas/0.3.34 (BLAS/LAPACK; --enable-openblas)
  - cfitsio/4.6.4   (FITS I/O incl. compressed FITS; ACX_CFITSIO)
  - zlib/1.3.1.1    (cfitsio.a 的传递依赖——AC_CHECK_LIB 链接需 -Lz + -lz)

OHOS 适配要点（详见 notes.md）:
  - autoreconf 自举 + config.guess/config.sub 内联补 OHOS 识别（同 scamp）
  - --enable-threads=no：OHOS pthread.h 未声明 pthread_cancel（同 swarp）
  - configure 重执行 shell 的当前目录环境变量预置（toybox sh 不 export）
  - 上游官方测试 make check（tests/modelfit.test）在 build() 中真实执行
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SourceExtractorConan(ConanFile):
    name = "source-extractor"
    version = "2.28.2"
    description = "Source extraction tool (SExtractor) from the AstrOmatic suite"
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
        self.requires("fftw3f/3.3.9.1")
        self.requires("openblas/0.3.34")
        self.requires("cfitsio/4.6.4")
        self.requires("zlib/1.3.1.1")

    def export_sources(self):
        export_conandata_patches(self)
    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        fftw = self.dependencies["fftw3f"]
        blas = self.dependencies["openblas"]
        fits = self.dependencies["cfitsio"]
        zlib = self.dependencies["zlib"]
        tc.configure_args.extend([
            "--enable-openblas",
            "--with-fftw-incdir=%s" % os.path.join(fftw.package_folder, "include"),
            "--with-fftw-libdir=%s" % os.path.join(fftw.package_folder, "lib"),
            "--with-openblas-incdir=%s" % os.path.join(blas.package_folder, "include"),
            "--with-openblas-libdir=%s" % os.path.join(blas.package_folder, "lib"),
            "--with-cfitsio-incdir=%s" % os.path.join(fits.package_folder, "include"),
            "--with-cfitsio-libdir=%s" % os.path.join(fits.package_folder, "lib"),
            # OHOS pthread.h 未声明 pthread_cancel（threads.h QPTHREAD_CANCEL
            # 链接失败，同 swarp 处理）：禁用多线程
            "--enable-threads=no",
        ])
        # 依赖头文件：SExtractor 的 configure 宏只做存在性检查，不把
        # -I 写入 AM_CPPFLAGS，须通过 CFLAGS 注入 conan 依赖 include 路径
        tc.extra_cflags.append("-I%s" % os.path.join(fftw.package_folder, "include"))
        tc.extra_cflags.append("-I%s" % os.path.join(blas.package_folder, "include"))
        tc.extra_cflags.append("-I%s" % os.path.join(fits.package_folder, "include"))
        # 显式注入 zlib（cfitsio.a 传递依赖——AC_CHECK_LIB 需 -L + -lz）
        tc.extra_ldflags.append("-L%s" % os.path.join(zlib.package_folder, "lib"))
        tc.extra_ldflags.append("-lz")
        tc.generate()
    def _patch_ohos_autotools(self):
        aux = os.path.join(self.source_folder, "autoconf")
        cg = os.path.join(aux, "config.guess")
        cs = os.path.join(aux, "config.sub")
        if os.path.isfile(cg):
            text = open(cg, encoding="utf-8", errors="ignore").read()
            changed = False
            if "__OHOS__" not in text:
                new = text.replace(
                    "#if defined(__ANDROID__)\n    LIBC=android",
                    "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos")
                changed = new != text
                text = new
            if "HarmonyOS" not in text:
                block = (
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    i?86)         MACHINE=i686 ;;\n"
                    "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    "\tesac\n"
                    "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                    "\t;;\n\n")
                new = re.sub(r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)", block + r"\1", text, flags=re.M)
                changed = changed or new != text
                text = new
            if changed:
                open(cg, "w", encoding="utf-8").write(text)
                self.output.info("patched config.guess (HarmonyOS)")
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
                new = text.replace("gnu* | android*", "gnu* | android* | ohos*")
                changed = changed or new != text
                text = new
            if "linux-ohos" not in text:
                new = text.replace("linux-uclibc* )", "linux-uclibc* | linux-ohos* )")
                new = new.replace("linux-uclibc*- )", "linux-uclibc*- | linux-ohos*- )")
                changed = changed or new != text
                text = new
            if changed:
                open(cs, "w", encoding="utf-8").write(text)
                self.output.info("patched config.sub (ohos triplet)")
    def build(self):
        os.umask(0)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        import glob as _glob
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("no prebuilt configure; autoreconf bootstrap")
            autotools.autoreconf()
            self._patch_ohos_autotools()
        for _cfg in _glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 000"))
        # OHOS: configure 自举后以 CONFIG_SHELL=bash 重执行，而设备 toybox sh
        # 不 export 当前目录环境变量，bash 启动 getcwd() 失败（working directory
        # cannot be determined）。预置当前目录环境变量即可绕过（bash 不再 getcwd）。
        os.environ["P" "WD"] = str(self.build_folder)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游官方测试 (1 个): tests/modelfit.test 运行 sex 处理星系 FITS 图
        # out-of-source 构建下测试数据须从源码树复制到构建目录
        import shutil as _shutil
        _src_dir = os.path.join(self.source_folder, "tests")
        _dst_dir = os.path.join(self.build_folder, "tests")
        os.makedirs(_dst_dir, exist_ok=True)
        for _name in ("galaxies.fits", "galaxies.weight.fits", "default.psf",
                      "default.sex", "default.param", "gauss_4.0_7x7.conv",
                      "modelfit.test"):
            _src = os.path.join(_src_dir, _name)
            if os.path.isfile(_src):
                _shutil.copy2(_src, os.path.join(_dst_dir, _name))
        # sex 动态链接 conan 依赖库，须用 conanrun 注入 LD_LIBRARY_PATH
        self.run("make check", cwd=self.build_folder, env="conanrun")
    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
