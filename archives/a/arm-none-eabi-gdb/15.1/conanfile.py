#!/usr/bin/env python3
"""Conan recipe for arm-none-eabi-gdb 15.1 — GNU debugger for ARM
embedded cross development (C/C++, autotools, GNU source).

Adaptation lessons applied:
- E007: config.guess cannot guess OHOS — pass --build/--host explicitly.
- GDB 15.1 configure REQUIRES GMP 4.2+/MPFR 3.1.0+ — requires them
  (published on ohpcd) + readline/ncurses/zlib/expat (--with-system-*).
- --without-python (avoid python dep); --disable-nls; --disable-werror.
- Homebrew lesson: ENV.deparallelize — version.c-stamp.tmp parallel
  build error — build with make -j1 (serial).
- self.run env arg must be a list — use command-prefix env vars.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class ArmNoneEabiGdbConan(ConanFile):
    name = "arm-none-eabi-gdb"
    version = "15.1"
    description = "GNU debugger for arm-none-eabi cross development"
    license = "GPL-3.0"
    homepage = "https://www.gnu.org/software/gdb/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "application"

    def requirements(self):
        # GDB 15.1 configure REQUIRES GMP 4.2+ / MPFR 3.1.0+ (not optional)
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")
        self.requires("readline/8.3")
        self.requires("ncurses/6.6")
        self.requires("zlib/1.3.1")
        self.requires("expat/2.8.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        incs, libs = [], []
        for d in ("gmp", "mpfr", "readline", "ncurses", "zlib", "expat"):
            pkg = self.dependencies[d].package_folder
            i = os.path.join(pkg, "include")
            l = os.path.join(pkg, "lib")
            if os.path.isdir(i):
                incs.append(f"-I{i}")
            if os.path.isdir(l):
                libs.append(f"-L{l}")
        cppflags = " ".join(incs) + " -D_GNU_SOURCE"
        ldflags = " ".join(libs)
        bld = "--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu"
        opts = ("--target=arm-none-eabi --without-python --disable-nls "
                "--disable-werror --with-system-readline --with-system-zlib "
                "--disable-sim")
        # E011 fix (sdcc/libgee 同款，完整三层)：
        # ① TMPDIR 指向非 hmdfs 可写目录——/storage 是 HMDFS 剥离权限，
        #    config.status 在 .cache/tmp（hmdfs）写 subs1.awk 报 Permission
        #    denied（CI 实证）；/data 下 chmod 生效（候选链）。
        # ② patch configure：ac_tmp 用 $TMPDIR 而非 ./confXXXXXX。
        # ③ umask 077→022：config.status 的 (umask 077 && mktemp) 生成
        #    0700 目录，hmdfs 上 other 用户不可读/写。
        import glob
        work_root = None
        for cand in ("/data/storage/el2/base/cache", "/data/cache",
                     self.build_folder):
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".gdb-w-probe")
                with open(probe, "w") as _f:
                    _f.write("x")
                os.remove(probe)
                work_root = cand
                break
            except OSError:
                continue
        if not work_root:
            raise ConanException("no writable non-hmdfs dir for gdb cfg-tmp")
        tmpdir = os.path.join(work_root, f"gdb-cfg-{os.getpid()}")
        os.makedirs(tmpdir, exist_ok=True)
        # gmp/mpfr 包 .la 文件 libdir 是 //lib（DESTDIR 安装 bug）——
        # libtool 链接 gdb 时读 libmpfr.la dependency_libs 引用
        # '//lib/libgmp.la' 找不到（CI/本地均报 cannot find the library
        # '//lib/libgmp.la'）。把依赖 .la 的 libdir/dependency_libs 修正为
        # 真实包路径（消费者侧修复，不改已合入的 gmp/mpfr 配方）。
        for d in ("gmp", "mpfr"):
            pkg = self.dependencies[d].package_folder
            la = os.path.join(pkg, "lib", f"lib{d}.la")
            if os.path.isfile(la):
                s = open(la).read()
                s2 = s.replace("libdir='//lib'", f"libdir='{pkg}/lib'")
                s2 = s2.replace("//lib/libgmp.la",
                                f"{self.dependencies['gmp'].package_folder}/lib/libgmp.la")
                if s2 != s:
                    open(la, "w").write(s2)
        cfg_scripts = glob.glob(os.path.join(self.source_folder, "**",
                                             "configure"),
                                recursive=True)
        for cfg_script in cfg_scripts:
            if not os.path.isfile(cfg_script):
                continue
            s = open(cfg_script).read()
            s2 = s.replace('mktemp -d "./confXXXXXX"',
                           'mktemp -d "$TMPDIR/confXXXXXX"')
            s2 = s2.replace("tmp=./conf$$-$RANDOM",
                            "tmp=$TMPDIR/conf$$-$RANDOM")
            s2 = s2.replace("(umask 077 && mktemp -d",
                            "(umask 022 && mktemp -d")
            if s2 != s:
                open(cfg_script, "w").write(s2)
        cfg = (f"TMPDIR='{tmpdir}' "
               f"CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ "
               f"CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}' ./configure {bld} {opts}")
        self.run(cfg, cwd=self.source_folder)
        # serial build (Homebrew: version.c-stamp.tmp parallel error)
        # 递归 configure-gdb（make 阶段）不继承主 configure 的 CPPFLAGS——
        # 会丢 readline include（checking readline/readline.h... no →
        # "readline development packages are probably missing"）。
        # make 变量显式传递，让 configure-gdb/configure-gdbserver 能找到依赖头。
        self.run(
            f"make -j1 all-gdb CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}'",
            cwd=self.source_folder)
        self.run(
            f"make -j1 install-gdb CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}' "
            f"DESTDIR={os.path.join(self.build_folder, 'gdb-stage')}",
            cwd=self.source_folder)

    def package(self):
        stage = os.path.join(self.build_folder, "gdb-stage")
        if not os.path.isdir(stage):
            raise ConanException(f"gdb staging missing: {stage}")
        for root, _dirs, files in os.walk(stage):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, stage)
                # gdb-stage 是 DESTDIR 安装（prefix=/usr/local）——产物在
                # usr/local/{bin,lib,share}/ 下；conan 惯例是 bin/lib/share
                # 直接在包根（test 与 PATH 均按 package_folder/bin 查找），
                # 复制时去掉 usr/local/ 前缀
                if rel.startswith("usr/local/"):
                    rel = rel[len("usr/local/"):]
                dst = os.path.join(self.package_folder, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        if not os.path.isfile(os.path.join(
                self.package_folder, "bin", "arm-none-eabi-gdb")):
            raise ConanException("arm-none-eabi-gdb binary missing in package")

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.output.info(f"PATH={bindir}")
