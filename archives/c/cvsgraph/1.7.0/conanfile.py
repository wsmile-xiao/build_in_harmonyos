#!/usr/bin/env python3
"""Conan recipe — cvsgraph 1.7.0 (Autotools).

CvsGraph renders a graphical representation (PNG/GIF/JPEG) of all revisions
and branches of a file in a CVS/RCS repository, using libgd for drawing.
Official source: https://www.vagrearg.org/content/cvsgraph (author's site;
SourceForge download URLs for this project return 404/403).

Build notes:
- configure.in is 2008-era autoconf 2.61 WITHOUT AC_CANONICAL_HOST: there is
  no config.guess/config.sub in the tarball and no triplet validation, but
  --host=<X> (without --build) still triggers autoconf's official
  cross_compiling=maybe path — used here so the configure survives CI
  workers whose sandbox forbids executing conftest binaries (cadaver
  #30663) while keeping full native run-checks where they work (device).
- gd detection: configure probes gdlib-config (not shipped by our gd conan
  package) or --with-gd=DIR. Neither is needed here: AutotoolsDeps exports
  gd/freetype -I/-L/-l into the env, so every AC_CHECK_LIB(gd, ...) link
  probe succeeds against the static libgd.a (plus shared libpng16) from
  gd/2.3.3.
- lex/yacc: the tarball ships pre-generated rcsl.c/rcsy.c/rcsy.h with newer
  mtimes than rcsl.l/rcsy.y, so make never regenerates them (no flex/bison
  needed at build time). build() defensively re-asserts that ordering.
- cvsgraph requires at least one of GIF/PNG/JPEG output support in gd
  (cvsgraph.c: #error when all absent). Dependency is gd/2.3.3 (static,
  zlib+libpng only): its libgd.a keeps the final binary's runtime closure
  down to libpng16.so.16 + libc. The fuller gd/2.3.3.1 (shared, with
  fontconfig/freetype) is NOT used because the published
  fontconfig/2.18.1 binary carries a baked absolute DT_NEEDED
  (/storage/Users/currentUser/.conan2/p/<hash>/p/lib/libexpat.so) that only
  resolves on machines whose conan cache sits at exactly that path — it
  broke CI (PR #10072 #47890: test_package "Error loading shared library
  .../.conan2/p/expat.../libexpat.so needed by libfontconfig.so.1") while
  passing on a device whose main cache happened to match. TTF text is
  therefore unavailable in this build (HAVE_GD_STRINGFT undefined); tests
  and docs use gd's built-in bitmap fonts (upstream use_ttf=false).
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CvsgraphConan(ConanFile):
    name = "cvsgraph"
    version = "1.7.0"
    description = "Graphical representation of revisions and branches in CVS/RCS repositories (renders via libgd)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.vagrearg.org/content/cvsgraph"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        # gd/2.3.3 (static, zlib+libpng): 见模块 docstring — gd/2.3.3.1 的
        # fontconfig 闭包带烤死绝对 DT_NEEDED（ohpcd 发布包缺陷），静态最小
        # 变体让运行期闭包只剩 libpng16.so.16 + libc。
        self.requires("gd/2.3.3")

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R1: 参数最少化. This configure has no AC_CANONICAL_HOST, so no
        # --build/--host args (they are accepted but unused); --prefix is
        # added by AutotoolsToolchain automatically.
        tc.generate()
        # Dependency -I/-L/-l into conanbuild env so configure's
        # AC_CHECK_LIB(gd ...)/AC_CHECK_LIB(freetype ...) link probes pass.
        AutotoolsDeps(self).generate()

    def build(self):
        # Fix: autoconf's `umask 077 && mktemp` idiom creates drwx--S---
        # temp dirs on OHOS (setgid without group execute) and configure
        # then fails to write probe files inside (fcrackzip-proven fix).
        conf = os.path.join(self.source_folder, "configure")
        replace_in_file(self, conf, "umask 077", "umask 022")

        # Insurance: keep the shipped parser/lexer outputs newer than their
        # .y/.l sources so automake never tries to regenerate them (the
        # build hosts may have no bison/flex; tar mtimes are already
        # correct, this only guards exotic filesystem behavior).
        for gen, src in (("rcsl.c", "rcsl.l"), ("rcsy.c", "rcsy.y"), ("rcsy.h", "rcsy.y")):
            gp = os.path.join(self.source_folder, gen)
            sp = os.path.join(self.source_folder, src)
            if os.path.getmtime(gp) < os.path.getmtime(sp):
                newer = os.path.getmtime(sp) + 1
                os.utime(gp, (newer, newer))

        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            # OHOS specifics (2026-09-14 真机实证，设备 10.62.178.77):
            # - /data/service/hnp/bin/bash 在 conan 构建(HMDFS 深)目录里 getcwd
            #   损坏（shell-init 噪音 + 旧 autoconf pwd 校验中止 configure）；
            #   /system/bin/sh 同目录探针干净 → 一律用 sh，且 CONFIG_SHELL
            #   同步固定，防止 autoconf 把 hnp bash 烤进 Makefile 的 SHELL。
            # - hmdfs 可能拒绝 shebang 脚本 exec → 显式 sh 调用绕过。
            # - /tmp 只读 → TMPDIR 指到 build 目录。
            # - 【关键】无 AC_CANONICAL_HOST → cross_compiling 恒为 no，
            #   configure 会真实运行 conftest；conftest 链接了 LIBS 里的
            #   -lgd，运行期必须给 LD_LIBRARY_PATH（依赖全是共享库），否则
            #   "cannot run C compiled programs"。从 self.dependencies 收集
            #   libdir 注入后，AC_CHECK_FUNCS 等运行检测全部真实通过。
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            # conftest 运行期库路径：与链接期同一组目录 + 追加保留环境原值
            # （CI worker 的 lld 依赖 profile 注入的 llvm/lib 下 libxml2.so.16，
            # 替换语义会把它丢掉——ohos-ci-environment-issues 记录部分 worker
            # 缺该库时所有链接步骤失败）。从 AutotoolsDeps 生成的
            # conanautotoolsdeps.sh 提取 -L 列表（单一事实源）。
            # ⚠️ 必须内联在命令前缀里：env="conanbuild" 会 source
            # conanbuildenv-*.sh，其 export LD_LIBRARY_PATH 会覆盖
            # Environment().define 的外层值（真机实测踩坑）。
            lib_dirs = []
            deps_sh = os.path.join(self.generators_folder, "conanautotoolsdeps.sh")
            if os.path.isfile(deps_sh):
                with open(deps_sh, encoding="utf-8", errors="ignore") as f:
                    # [^\s"] 防止把 shell 行尾引号吃进路径（实测踩坑）
                    lib_dirs = re.findall(r"-L([^\s\"]+)", f.read())
            ldlp = os.pathsep.join(lib_dirs)
            self.output.info(f"conftest LD_LIBRARY_PATH prefix: {ldlp}")
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("CONFIG_SHELL", "/system/bin/sh")
            # --host 不带 --build 是 autoconf 2.5x 的官方 cross 触发器：
            # cross_compiling 置为 maybe（configure L1130，即使无
            # AC_CANONICAL_HOST 也生效）。conftest 可运行时（真机原生构建）
            # 正常通过并保持 no；被 CI worker 沙箱拦截时（cadaver #30663
            # 实证：conftest 可执行文件禁止运行，症状为 "checking whether
            # the C compiler works... no"）自动降级 cross 模式继续，链接期
            # AC_CHECK_LIB(gd/...) 探测不受影响；memset/strdup/strtol 在
            # cross 模式缺 HAVE_ 宏但源码无任何守卫（libc 直接提供，无害）。
            # CC 由工具链环境显式指定，ac_tool_prefix 前缀查找不参与。
            # --prefix=/ 与 AutotoolsToolchain 默认一致（本 conan 发行版
            # install() 自动注入 DESTDIR=package_folder；绝对 prefix 会叠出
            # <pkg>/storage/... 嵌套布局，真机实测踩坑）。
            with env.vars(self).apply():
                self.run(
                    f'TMPDIR="{tmpdir}" CONFIG_SHELL=/system/bin/sh '
                    f'LD_LIBRARY_PATH="{ldlp}:$LD_LIBRARY_PATH" '
                    f'/system/bin/sh "{conf}" --prefix=/ --host=aarch64-linux-ohos',
                    env="conanbuild")
        else:
            autotools.configure()
        # R9/-j1: OHOS does not support the make jobserver (mkfifo)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
