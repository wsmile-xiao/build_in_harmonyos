#!/usr/bin/env python3
"""Conan recipe — libcupsfilters 2.2.1 (OpenPrinting).

libcupsfilters 是 OpenPrinting 的打印过滤/转换库，提供
光栅图像处理、PDF 生成、色彩管理等功能，供打印过滤器
和驱动使用。

构建：autotools（release tarball 含预生成 configure/Makefile.in）
依赖：cups/2.4.19（硬，cups3→cups2 fallback）、zlib/1.3.1（硬）、
      pdfio/1.6.5（硬，>= 1.6.4）
      libpng/libtiff/libjpeg/libexif/lcms2/fontconfig/libjxl（可选，
      --without-xxx 可禁用）
许可证：Apache-2.0

OHOS 适配要点：
  1. 预生成 configure 里 config.guess（2022 版）不认识 OHOS，
     需手动 patch config.guess/config.sub 识别 HarmonyOS/OHOS
  2. 显式设 --build/--host=aarch64-ohos-linux-gnu，绕过 config.guess
  3. release tarball 含预生成 configure，无需 autoreconf
     （CI worker 缺 aclocal/autopoint）
  4. --without-jpegxl（libjxl 可选，避免额外依赖）
  5. --disable-dbus（dbus 可选，仓库没有 dbus-1）
"""
import os
import re

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    copy,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibcupsfiltersConan(ConanFile):
    name = "libcupsfilters"
    version = "2.2.1"
    description = "OpenPrinting print filter/convert library"
    license = "Apache-2.0"
    homepage = "https://github.com/OpenPrinting/libcupsfilters"
    url = "https://github.com/OpenPrinting/libcupsfilters"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # libcupsfilters 硬依赖
        self.requires("cups/2.4.19")
        self.requires("zlib/1.3.1.1")
        self.requires("pdfio/1.6.5")
        # lcms2 是 PDF 色彩管理硬依赖（configure.ac PKG_CHECK_MODULES LCMS lcms2）
        self.requires("lcms2/2.19")

    def source(self):
        # release tarball 含预生成 configure，CI 优先用
        # 本地 GitHub release 下载超时时，fallback 到 codeload 镜像
        # codeload 是 source archive，需 autoreconf 生成 configure
        src = self.conan_data["sources"]
        try:
            get(self, **src, strip_root=True)
        except Exception:
            self.output.info("  [fallback] GitHub release 下载失败，改用 codeload 镜像")
            get(
                self,
                url="https://codeload.github.com/OpenPrinting/libcupsfilters/tar.gz/refs/tags/2.2.1",
                sha256="98b286aea9f2ccd7d0fd0bff663e110992559adeee8cf768071e56a8ca1a4736",
                filename="libcupsfilters-2.2.1.tar.gz",
                strip_root=True,
            )

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 不传 --build/--host：让已 patch 的 config.guess 自动识别 OHOS，
        # CC/CFLAGS 由 profile 通过 AutotoolsToolchain 注入。
        # 之前传 --build=--host=aarch64-ohos-linux-gnu 会让 configure 找
        # 不存在的 aarch64-ohos-linux-gnu-gcc，conftest 链接失败
        # (configure: error: C compiler cannot create executables)。
        # OHOS 交叉编译：configure 尝试运行编译出的测试程序会失败，
        # 用 ac_cv_prog_cc_c_o=yes + cache 预设绕过运行测试
        tc.configure_args.append("ac_cv_prog_cc_c_o=yes")
        tc.configure_args.append("ac_cv_prog_cc_cross=yes")
        tc.configure_args.append("cross_compiling=yes")
        tc.configure_args.append("ac_cv_func_fork=yes")
        tc.configure_args.append("ac_cv_func_vfork=yes")
        tc.configure_args.append("ac_cv_func_setenv=yes")
        # 禁用可选依赖（避免引入仓库没有的包）
        # --disable-imagefilters 一次禁用 lcms2/jpeg/png/tiff/libexif 等
        # 图像处理依赖，只保留核心打印过滤功能
        tc.configure_args.append("--disable-imagefilters")
        tc.configure_args.append("--without-jpegxl")
        tc.configure_args.append("--without-jpeg")
        tc.configure_args.append("--without-png")
        tc.configure_args.append("--without-tiff")
        tc.configure_args.append("--without-fontconfig")
        tc.configure_args.append("--disable-dbus")
        tc.configure_args.append("--disable-exif")
        # OHOS HMDFS 不允许 mkfifo，禁用 make jobserver（-j1）
        tc.make_args.append("-j1")
        # 避免 autoreconf（release tarball 含预生成 configure）
        tc.generate()
        # libcupsfilters configure 用 pkg-config 查 cups/pdfio/zlib，
        # 必须同时生成 AutotoolsDeps（CFLAGS/LIBS）和 PkgConfigDeps（.pc）
        deps = AutotoolsDeps(self)
        deps.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        # 0. Patch configure: umask 077 → 022
        #    OHOS HMDFS 在 umask 077 下创建临时目录得到 2700 权限，
        #    config.status 的 subs1.awk 写入失败 (Permission denied)。
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(configure_path, "w") as f:
                    f.write(content)
                self.output.info("  [ok] configure: umask 077 → 022")
            else:
                self.output.info("  [ok] configure: umask 077 not found, skipping")
        # 1. Patch config.guess/config.sub 识别 OHOS
        self._patch_config_for_ohos()
        # 2. release tarball 含预生成 configure，直接 configure + make
        #    libcupsfilters Makefile.in 用源码内构建（.c.o 规则引用无路径 $<），
        #    Conan Autotools 默认在独立 build 目录跑 make 会找不到头文件。
        #    修复：chdir 到 source_folder 跑 configure + make（源码内构建）。
        cwd = os.getcwd()
        try:
            os.chdir(self.source_folder)
            autotools = Autotools(self)
            # 不传 args：让 generate() 里 tc.configure_args 的全部参数
            # （--disable-imagefilters、ac_cv_prog_cc_cross=yes 等）自动生效。
            # 之前传 args=[...] 会覆盖 generate() 的 configure_args，
            # 导致 --disable-imagefilters 等丢失，configure 用错误参数运行。
            autotools.configure()
            # make 时构建辅助程序（gen-lorem-text 等）会运行，
            # 需设 LD_LIBRARY_PATH 让它们找到 lcms2/cups 等共享库。
            # 用 os.environ 直接设置（Environment API 在子 shell 可能失效）。
            extra_lib_paths = set()
            for dep in self.dependencies.host.values():
                extra_lib_paths.update(dep.cpp_info.libdirs)
            for dep in self.dependencies.build.values():
                extra_lib_paths.update(dep.cpp_info.libdirs)
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join(
                list(extra_lib_paths) + ([existing] if existing else [])
            )
            autotools.make()
        finally:
            os.chdir(cwd)

    def _patch_config_for_ohos(self):
        """Patch config.guess/config.sub 识别 HarmonyOS/OHOS."""
        for fn in ("config.guess", "config.sub"):
            path = os.path.join(self.source_folder, fn)
            if not os.path.isfile(path):
                continue
            with open(path, "r") as f:
                content = f.read()
            if "HarmonyOS" in content:
                continue
            # 在 NetBSD case 之前插入 HarmonyOS case
            if "    *:NetBSD:*:*)" in content:
                block = (
                    '    *:HarmonyOS:*:*)\n'
                    '\tcase "$UNAME_MACHINE" in\n'
                    '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                    '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                    '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                    '\t    i?86)          MACHINE=i686 ;;\n'
                    '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                    '\tesac\n'
                    '\tGUESS=${MACHINE}-unknown-linux-gnu\n'
                    '\t;;\n\n'
                    '    *:NetBSD:*:*)'
                )
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                with open(path, "w") as f:
                    f.write(content)
                self.output.info(f"  [ok] Patched {fn} for HarmonyOS")

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # libcupsfilters 用源码内构建，install 也要在 source_folder 跑
        cwd = os.getcwd()
        try:
            os.chdir(self.source_folder)
            autotools = Autotools(self)
            autotools.install()
        finally:
            os.chdir(cwd)

        # 清理不需要的文件
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libcupsfilters")
        self.cpp_info.libs = ["cupsfilters"]
        # libcupsfilters 用 --prefix=.../usr 安装，头文件在 usr/include
        self.cpp_info.includedirs = ["usr/include"]
        self.cpp_info.libdirs = ["lib"]
        # libcupsfilters 依赖 cups/pdfio/zlib
        self.cpp_info.requires = [
            "cups::cups",
            "pdfio::pdfio",
            "zlib::zlib",
            "lcms2::lcms2",
        ]
