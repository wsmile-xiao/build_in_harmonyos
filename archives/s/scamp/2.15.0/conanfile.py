#!/usr/bin/env python3
"""Conan recipe for scamp 2.15.0 (astrometric calibration tool, autotools).

Dependencies:
  - fftw3f/3.3.9.1  (single-precision FFTW, published)
  - openblas/0.3.34 (BLAS/LAPACK, published)
  - curl           (system/precompiled via cmd-pkgs, not published as conan recipe)

scamp is a command-line tool; the package contains only the `scamp` binary.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ScampConan(ConanFile):
    name = "scamp"
    version = "2.15.0"
    description = "Compute astrometric solutions from SExtractor catalogs"
    license = "GPL-3.0-or-later"
    homepage = "https://www.astromatic.net/software/scamp"
    url = "https://github.com/astromatic/scamp"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # GitHub archive tarball 无预生成 configure，需 autoreconf 自举
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        self.requires("fftw3f/3.3.9.1")
        self.requires("openblas/0.3.34")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Dependency include/lib dirs (from conan packages)
        fftw = self.dependencies["fftw3f"]
        blas = self.dependencies["openblas"]
        tc.configure_args.extend([
            "--with-fftw-incdir=%s" % os.path.join(fftw.package_folder, "include"),
            "--with-fftw-libdir=%s" % os.path.join(fftw.package_folder, "lib"),
            "--enable-openblas",
            "--with-openblas-incdir=%s" % os.path.join(blas.package_folder, "include"),
            "--with-openblas-libdir=%s" % os.path.join(blas.package_folder, "lib"),
        ])
        tc.generate()

    def _patch_ohos_autotools(self):
        """对 autoreconf 生成的 config.guess/config.sub 内联补 OHOS 识别。

        GitHub archive tarball 无预生成 configure，须 autoreconf 自举；
        conan 的 automake 工具链生成的 config.guess/config.sub 不含
        HarmonyOS 分支，configure 会报 "cannot guess build type"。
        此处等效实现 patch-autotools-ohos.pl 的替换逻辑（不依赖外部脚本，
        因为 SKILL_ROOT 脚本不在 CI 构建环境内）。
        """
        import glob as _glob
        aux = os.path.join(self.source_folder, "autoconf")
        cg = os.path.join(aux, "config.guess")
        cs = os.path.join(aux, "config.sub")
        # --- config.guess ---
        if os.path.isfile(cg):
            text = open(cg, encoding="utf-8", errors="ignore").read()
            changed = False
            if "__OHOS__" not in text:
                # 1.1 LIBC=ohos 分支（接在 __ANDROID__ 后）
                new = text.replace(
                    "#if defined(__ANDROID__)\n    LIBC=android",
                    "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos")
                changed = new != text
                text = new
            if "HarmonyOS" not in text:
                # 1.2 通用系统识别块（插到 NetBSD case 前）
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
                self.output.info("已修补 config.guess: 加入 HarmonyOS 识别")
        # --- config.sub ---
        if os.path.isfile(cs):
            text = open(cs, encoding="utf-8", errors="ignore").read()
            changed = False
            if "ohos-linux" not in text:
                # 匹配整个 android-linux 分支块（含缩进与 ;;），在其后插入 ohos-linux 分支
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
                self.output.info("已修补 config.sub: 加入 ohos triplet 支持")

    def build(self):
        # OHOS: config.status 临时目录创建需 umask 000（hmdfs 上 077 会 Permission denied）
        os.umask(0)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        import glob as _glob
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
            self._patch_ohos_autotools()
        # OHOS: configure 生成的 config.status 用 umask 077 建临时目录会失败，改为 000
        for _cfg in _glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
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
        # 上游官方测试（5 个，含 4 个 C 测试 + 1 个 Python 集成测试）
        # out-of-source 构建下测试程序用相对路径读 tests/extra/ 数据，
        # 需先把测试数据从源码树复制到构建目录（本地 in-source 构建无此问题）
        import shutil as _shutil
        for _name in ("extra", "test_integration01.conf"):
            _src = os.path.join(self.source_folder, "tests", _name)
            _dst = os.path.join(self.build_folder, "tests", _name)
            if os.path.isdir(_src):
                _shutil.copytree(_src, _dst, dirs_exist_ok=True)
            elif os.path.isfile(_src):
                _shutil.copy2(_src, _dst)
        # make check 的测试程序动态链接 conan 依赖库（libopenblas/libfftw3f），
        # 必须用 conanrun 运行环境注入 LD_LIBRARY_PATH，否则运行时加载失败（CI Error 2）
        # test_integration01.py 依赖 numpy/astropy（Python 包），CI worker 未安装时
        # 用 TESTS= 过滤只跑 4 个 C 测试，避免 make check 整体失败（参考 datamash 做法）
        check_args = []
        _py_ok = self.run(
            'python3 -c "import numpy, astropy"',
            cwd=self.build_folder, env="conanrun", ignore_errors=True) == 0
        if not _py_ok:
            self.output.info("python3 缺少 numpy/astropy，跳过 test_integration01.py（仅跑 4 个 C 测试）")
            # 必须用双引号包裹 TESTS 值，否则 shell 单词分割会把后续测试名解析为
            # 额外 make 目标，导致只有第一个测试被执行（虚假通过）
            check_args.append('TESTS="test_chealpix test_chealpixstore '
                              'test_crossid_single_catalog test_crossid_single_catalog_moving"')
        self.run("make check " + " ".join(check_args), cwd=self.build_folder, env="conanrun")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # scamp 是命令行工具，无库文件，不设置 cpp_info.libs
