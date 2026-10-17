#!/usr/bin/env python3
"""Conan recipe for the GnuCOBOL 3.2 runtime library (libcob.so.4) on OpenHarmony/HarmonyOS.

这个包只交付 GnuCOBOL 的 **运行时共享库**，不交付编译器：

  * conan 包名 `libcob4` 取自库本身自报的 ABI SONAME —— `libcob/Makefile.am` 里
        libcob_la_LDFLAGS = ... -version-info 6:0:2
    libtool 语义为 `libNAME.so.(current-age).age.revision`，即
        SONAME    = libcob.so.(6-2)      = libcob.so.4
        ABI 文件名 = libcob.so.4.2.0
    所以「libcob4」就是 ABI 主版本号为 4 的 libcob，不是另一个上游项目
    （上游仓库与 gnucobol/3.2 包完全相同）。
  * 交付物只有 `lib/libcob.so*`（含 soname/soname-link 符号链接）与公共头
    `include/libcob.h` + `include/libcob/{common,version,cobgetopt}.h`；
    编译器 `cobc`/`cobcrun`、copybook/配置目录、CBL_OC_DUMP.so 均**不**属于本包
    （它们是 gnucobol/3.2 的交付物）。需要编译器请依赖 gnucobol/3.2。

构建策略（与 gnucobol/3.2 保持同源同补丁，理由见 notes.md）：

  * 源码、SHA256、7 个 OHOS 可移植性补丁与 gnucobol/3.2 逐字相同（含
    `0004-libcob-call.c.patch`、`0005-libcob-common.c.patch` —— 这两条正是
    HarmonyOS `fmemopen` 不可用、临时目录可能只读时的运行时修复）。
  * 仍然走完整 `./configure && make`：GnuCOBOL 的上游测试套件
    (tests/testsuite，1226 用例) 是经 `cobc` 驱动的，只构建 libcob 子目录
    无法执行它。为满足「上游测试必须真跑」的口径，本包照跑完整测试套件，
    只是 install 阶段**只装 libcob 子目录**。
  * `make -C libcob install` 装库与子目录头；顶层的伞头文件 `libcob.h`
    （`Makefile.am` 里 `include_HEADERS = libcob.h`）由配方手工复制。
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libcob4Conan(ConanFile):
    name = "libcob4"
    version = "3.2"
    description = "GnuCOBOL 3.2 runtime library (libcob.so.4) — COBOL runtime and C API"
    license = "LGPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gnucobol/"
    url = "https://www.gnu.org/software/gnucobol/"
    topics = ("cobol", "gnucobol", "runtime", "libcob")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.configure_args.extend([
            "--with-math=gmp",
            "--with-curses=no",
            "--with-json=no",
            "--with-db=no",
            "--with-xml2=no",
        ])
        env = tc.environment()
        if str(self.settings.os) == "OHOS":
            env.define("STRIP", ":")
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)

        # configure 脚本里有一处被写坏的非 ASCII 字节（"clang <0xfc>rototype warning"），
        # 某些 host 的 shell/awk 会因此报语法错。替换成 ASCII 后再跑。
        configure_path = os.path.join(self.source_folder, "configure")
        typo = b"clang \xfcrototype warning"
        replacement = b"clang prototype warning"
        with open(configure_path, "rb") as source_file:
            configure_content = source_file.read()
        if configure_content.count(typo) != 2:
            raise ConanException("Unexpected configure encoding typo count")
        with open(configure_path, "wb") as source_file:
            source_file.write(configure_content.replace(typo, replacement))

        # E089: patch 0006 modifies configure.ac, which would make `make`
        # regenerate aclocal.m4/configure/Makefile.in via aclocal/autoconf/
        # automake; the OHOS build host has no automake, and the release
        # tarball already ships complete generated files. Align the mtimes
        # of the shipped generated files with a time strictly newer than
        # configure.ac (the patched configure.ac mtime is the newest input)
        # but older than the Makefile that configure will generate, so make
        # treats them as up to date without re-running config.status.
        # 若 make 重新生成 configure，就会把上面那处字节替换抹掉。
        import time
        _gen_mtime = time.time()
        for _f in ("aclocal.m4", "configure", "config.h.in", "Makefile.in"):
            _p = os.path.join(self.source_folder, _f)
            if os.path.exists(_p):
                os.utime(_p, (_gen_mtime, _gen_mtime))
        # The shipped man pages (cobcrun.1, cob-config.1, cobc.1) depend on
        # configure.ac in their make rules; after patch 0006 touches
        # configure.ac, make would regenerate them via help2man, which is
        # not installed on the OHOS build host. Bump their mtimes too so
        # make keeps the pre-generated man pages.
        for _root, _dirs, _files in os.walk(self.source_folder):
            for _fn in _files:
                if _fn.endswith(".1"):
                    _p = os.path.join(_root, _fn)
                    os.utime(_p, (_gen_mtime, _gen_mtime))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        check_log = os.path.join(self.build_folder, "libcob4-upstream-check.log")
        quoted_log = shlex.quote(check_log)
        rc = self.run(
            "make MAKEINFO=true -j1 check > " + quoted_log + " 2>&1; "
            "rc=$?; "
            "grep -a -E 'tests behaved as expected|tests were skipped|tests were run|failed \\(' "
            + quoted_log
            + " || true; "
            "if grep -aqE ':( FAILED| XPASS| ERROR)' " + quoted_log + "; then "
            + "  echo 'make check: FAIL/XPASS/ERROR detected in testsuite log'; rc=1; "
            + "fi; "
            "exit $rc"
        )
        if rc != 0:
            raise ConanException("make check failed (exit code %d), see %s" % (rc, check_log))

    def package(self):
        # 只 install libcob 子目录：库 + 该子目录的 pkginclude 头文件。
        # 编译器、copybook、配置目录等 gnucobol/3.2 的交付物不进本包。
        autotools = Autotools(self)
        autotools.install(args=["-C", "libcob"])

        # 顶层伞头文件 libcob.h（-I<includedir> 后 `#include <libcob.h>` 的入口）
        # 由顶层 Makefile.am 的 `include_HEADERS = libcob.h` 安装，
        # `make -C libcob install` 覆盖不到，手工补。
        copy(self, "libcob.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)

        # libtool 归档文件与静态库不属于共享库交付物
        for _f in ("lib/libcob.la", "lib/libcob.a"):
            _p = os.path.join(self.package_folder, _f)
            if os.path.exists(_p):
                os.remove(_p)

    def package_info(self):
        self.cpp_info.libs = ["cob"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.requires = ["gmp::gmp"]
