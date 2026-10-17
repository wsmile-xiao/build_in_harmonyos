#!/usr/bin/env python3
"""libydpdict — ydpdict 词典支持库（autotools + libtool）。

适配要点：
1. R26：系统同名库按静态产物构建（默认 shared=False）。
2. E007：config.guess / config.sub 需补 HarmonyOS 分支（补丁）。
3. E543：上游发布包的 ltmain.sh 与其 aclocal.m4 声明的 libtool 版本错配，
   由其生成的 libtool 缺少 func_dirname / func_opt_split 等 9 个内建函数，
   `--mode=link` 静默不产出 .so。source() 用 GNU libtool 官方包内版本精确匹配
   （package_revision=1.3293）的 ltmain.sh 覆盖上游残缺文件。
4. E543 同源：conan 用 /bin/sh（本平台为 MIRBSD ksh）启动 configure，而 ohpcd
   profile 的 [buildenv] 导出 SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash。
   configure 于是在 ksh 下测得 ECHO='print -r --'（ksh 内建），却用 bash 执行
   config.status → bash 无 print → "print: command not found"（config.status:712/724），
   最终 "config.status: error: could not setup config files machinery"（build() 失败）。
   profile [buildenv] 优先级高于配方 buildenv_info，故在 build() 中以命令前缀赋值
   调用 configure（POSIX 语义中前缀赋值优先于环境变量），把整条链统一到 /bin/sh：
   configure → config.status → 生成的 libtool → Makefile 的 SHELL。
5. VPATH 构建：上游 AM_CPPFLAGS 只指向 top_srcdir/include，源码外构建时生成的
   include/ydpdict.h 位于 top_builddir/include，src/ydpdict.c 因此报
   "fatal error: 'ydpdict.h' file not found"。build() 在 configure 时补入构建目录
   include 路径（$PWD/include），使其随 CPPFLAGS 进入生成的 Makefile。
6. HMDFS 以目录“组位”授权：autoconf config.status 以
   `(umask 077 && mktemp -d ./confXXXXXX)` 创建临时目录，而 mkdtemp 语义使其权限恒为
   0700（umask 无法放宽），新目录所有者在 HMDFS 上被映射为固定 uid，进程按组位判定
   不可写，写 subs1.awk 时报 "Permission denied"。build() 在构建目录安装 mktemp 垫片
   （以 umask 002 建目录并补 2770，组可写）并前置 PATH，覆盖 configure/make/install。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


_MKTEMP_SHIM = r"""#!/bin/sh
# 本机(HMDFS/hmmac=use_task)兼容版 mktemp 垫片。
# 系统 mktemp -d 以 0700 建目录；本文件系统把新目录所有者映射为固定 uid，
# 进程 uid 与之一致性无法保证，0700 目录因此对当前进程不可写
# （autoconf config.status 的 ./confXXXXXX 临时目录即在此处失败）。
# 本垫片改为 umask 002 建目录/文件（组可写，实测 2771 可写），保持唯一性。
dir=0
dry=0
while [ $# -gt 0 ]; do
  case "$1" in
    -d) dir=1; shift ;;
    -u) dry=1; shift ;;
    -q) shift ;;
    --) shift; break ;;
    -*) shift ;;
    *) break ;;
  esac
done
tmpl="$1"
[ -n "$tmpl" ] || tmpl="${TMPDIR:-/tmp}/tmp.XXXXXX"
case "$tmpl" in
  *XXXXXX) pre="${tmpl%XXXXXX}" ;;
  *) pre="$tmpl" ;;
esac
i=0
while [ "$i" -le 500 ]; do
  cand="${pre}$$-$i"
  if [ "$dry" = 1 ]; then
    printf '%s\n' "$cand"
    exit 0
  fi
  if [ "$dir" = 1 ]; then
    if ( umask 002; mkdir "$cand" ) 2>/dev/null; then
      chmod 2770 "$cand" 2>/dev/null
      printf '%s\n' "$cand"
      exit 0
    fi
  else
    if ( umask 002; set -C; : > "$cand" ) 2>/dev/null; then
      printf '%s\n' "$cand"
      exit 0
    fi
  fi
  i=$((i + 1))
done
exit 1
"""


class LibydpdictConan(ConanFile):
    name = "libydpdict"
    version = "1.0.4"
    description = "ydpdict dictionary support library"
    license = "LGPL-2.1"
    homepage = "https://toxygen.net/ydpdict/"
    url = "https://github.com/wojtekka/libydpdict"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # E543：见模块 docstring。用官方 libtool 包内的 ltmain.sh 覆盖残缺件。
        aux = self.conan_data.get("libtool_source")
        if aux:
            aux_dir = os.path.join(self.source_folder, "_libtool_source")
            get(self, **aux, destination=aux_dir)
            copy(
                self,
                "libtool-2.4/libltdl/config/ltmain.sh",
                src=aux_dir,
                dst=self.source_folder,
                keep_path=False,
            )
            rmdir(self, aux_dir)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            # R26：系统同名库构建静态产物
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        # 适配要点 4：Autotools.configure() 内部走 conanfile.run(cmd)，无法传环境
        # 前缀，而 profile [buildenv] 的 SHELL/CONFIG_SHELL 会覆盖配方 env。
        # 这里暂存工具链参数，供 build() 自行以命令前缀方式调用 configure。
        self._ohc_configure_args = list(tc.configure_args)

    def build(self):
        apply_conandata_patches(self)
        # 适配要点 6：HMDFS 以目录“组位”授权。CI worker 默认 umask 022 会让
        # config.status/make 的临时目录（mktemp -d）以 700 创建，组不可写，
        # 报 “can't create ./confXXXXXX/subs1.awk: Permission denied”。
        # 在 conan 进程内设 umask 002（configure/make/install 子进程继承），
        # 使临时目录为 775，组可写。
        os.umask(0o002)
        # 适配要点 6：HMDFS 按目录“组位”授权，而 config.status 的临时目录由
        # mktemp -d 创建（mkdtemp 语义：权限恒为 0700，umask 无法放宽），新目录
        # 所有者在 HMDFS 上被映射为固定 uid，进程按组位判定不可写，报
        # "can't create ./confXXXXXX/subs1.awk: Permission denied"。
        # 方案：把本机验证过的 mktemp 垫片装进构建目录并前置 PATH
        # （垫片以 umask 002 建目录并补 2770，组可写），覆盖 configure/make/install。
        shim_bin = os.path.join(self.build_folder, "shimbin")
        os.makedirs(shim_bin, exist_ok=True)
        shim_path = os.path.join(shim_bin, "mktemp")
        with open(shim_path, "w") as fh:
            fh.write(_MKTEMP_SHIM)
        os.chmod(shim_path, 0o755)
        os.environ["PATH"] = shim_bin + os.pathsep + os.environ.get("PATH", "")
        autotools = Autotools(self)
        configure = os.path.join(self.source_folder, "configure")
        args = " ".join(getattr(self, "_ohc_configure_args", []))
        # 适配要点 4：命令前缀赋值优先于任何环境文件导出的同名变量，
        # 使 configure/config.status/生成的 libtool 与 Makefile 都用 /bin/sh。
        # 适配要点 5：VPATH 构建下生成的 include/ydpdict.h 在构建目录，
        # 需显式补入（$PWD 即 configure 的工作目录 = conan 构建目录）。
        self.run(
            'PATH="{}:$PATH" CPPFLAGS="-I$PWD/include $CPPFLAGS" '
            'SHELL=/bin/sh CONFIG_SHELL=/bin/sh "{}" {}'.format(shim_bin, configure, args)
        )
        make_program = self.conf.get("tools.gnu:make_program", default="make")
        self.run('PATH="{}:$PATH" "{}" -j1'.format(shim_bin, make_program))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["ydpdict"]
