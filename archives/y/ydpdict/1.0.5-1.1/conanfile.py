#!/usr/bin/env python3
"""ydpdict — YDP 词典（波兰语系）全屏检索客户端（autotools + libtool）。

适配要点：
1. package_type=application：产物仅 bin/ydpdict（无库文件），因此不建
   cpp_info.libs；软件级 commands.json 由 R38 要求（见 archives/y/ydpdict/）。
2. R26/R4：ncurses 依赖取静态宽字符库（libncursesw.a）——OHOS 上以共享形态
   安装 ncurses 会与系统库冲突（junk 门禁同源教训），静态链接杜绝该风险。
3. AM_GNU_GETTEXT([external])：configure 走 NLS 分支，需要 po/Makefile.in.in
   （上游发布包已含）。以 `--disable-nls` 关闭翻译编译，避免 CI 干净环境额外
   引入 gettext 工具链（R33/R36：不依赖未声明的外部工具）。
4. libao 为可选依赖（configure.ac 中 PKG_CHECK_MODULES([AO],[ao],...,[ : ])
   带降级分支）：默认 --without-libao。OHOS 无 /dev/dsp，上游代码自动回退到
   config_player 指定的外部播放器路径（ydpsound.c play_linux）。
5. E543 同源（参见 libydpdict 1.0.4 配方与知识条目）：profile [buildenv] 导出
   SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash，而 conan 以 /bin/sh（本平台为
   MIRBSD ksh）启动 configure。configure 在 ksh 下测得 ECHO='print -r --'，
   config.status 却由 bash 执行 → "print: command not found"，链尾报
   "config.status: error: could not setup config files machinery"。
   build() 以命令前缀赋值（POSIX：前缀赋值优先于环境变量）把 configure →
   config.status → 生成的 libtool → Makefile 整条链统一到 /bin/sh。
6. HMDFS(Hmmac use_task) 以目录“组位”授权：config.status 以
   `(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录，mkdtemp 语义使其权限恒为
   0700（umask 无法放宽），新目录所有者被文件系统映射为固定 uid，进程按组位
   判定不可写，写 subs1.awk 时报 "Permission denied"。
   build() 在构建目录装 mktemp 垫片（umask 002 建目录并补 2770，组可写）并
   前置 PATH，覆盖 configure/make/install 全程。
7. PKG_CHECK_MODULES([YDPDICT],[libydpdict >= 0.99.3])：依赖包 1.0.4 的
   libydpdict.pc 以 prefix=/ 生成（DESTDIR 安装的中间产物），直接交给
   pkg-config 会把 -I/-L 指向主机根目录。generate() 用依赖自身 cpp_info 的
   私有路径覆盖 YDPDICT_CFLAGS/YDPDICT_LIBS——pkg.m4 检测到这两个环境变量已
   定义即跳过 pkg-config 探测（R49：只注入依赖私有路径，不碰共享前缀）。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# HMDFS 兼容版 mktemp 垫片（与 libydpdict 1.0.4 配方同源，见适配要点 6）。
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


class YdpdictConan(ConanFile):
    name = "ydpdict"
    version = "1.0.5-1.1"
    description = "YDP dictionaries client (full-screen ncurses TUI)"
    license = "GPL-2.0-or-later"
    homepage = "https://toxygen.net/ydpdict/"
    url = "https://github.com/wojtekka/ydpdict"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"libao": [True, False]}
    default_options = {"libao": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 宽字符 ncurses（静态）：configure 的 AC_CHECK_LIB([ncursesw],[initscr])
        # 与 AC_CHECK_HEADER([ncursesw/ncurses.h]) 均由此满足。
        self.requires("ncurses/6.6")
        # 词典引擎：configure 的 PKG_CHECK_MODULES([YDPDICT],[libydpdict >= 0.99.3])
        self.requires("libydpdict/1.0.4")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 适配要点 3：关闭 NLS，规避 build 期 gettext 工具链依赖。
        tc.configure_args.append("--disable-nls")
        # 适配要点 4：libao 可选，默认关闭。
        if not self.options.libao:
            tc.configure_args.append("--without-libao")
        # 适配要点 7：用依赖私有路径覆盖 pkg-config 探测结果。
        dep = self.dependencies["libydpdict"]
        cflags = " ".join("-I" + d for d in dep.cpp_info.includedirs)
        libs = " ".join(["-L" + d for d in dep.cpp_info.libdirs] +
                        ["-l" + lib for lib in dep.cpp_info.libs])
        env = tc.environment()
        # 适配要点 8：ncurses 依赖的 include/lib 必须显式注入编译与链接环境。
        # 上游 configure.ac 用 AC_CHECK_HEADER([ncursesw/ncurses.h])、
        # AC_CHECK_HEADER([curses.h])、AC_CHECK_LIB([ncursesw],[initscr]) 探测，
        # 而该包只装 include/curses.h 与 lib/libncursesw.a（无 include/ncursesw/）。
        # Conan 不会自动把依赖目录写进 CPPFLAGS/LDFLAGS，缺 -I 时连 curses.h 都
        # 找不到，configure 走 AC_MSG_ERROR 分支报 "checking for Unicode-aware
        # ncurses... error: no"；补 -I/-L 后走 maybe 分支正常继续。
        nc = self.dependencies["ncurses"]
        env.append("CPPFLAGS", " ".join("-I" + d for d in nc.cpp_info.includedirs))
        env.append("LDFLAGS", " ".join(["-L" + d for d in nc.cpp_info.libdirs] +
                                      ["-l" + lib for lib in nc.cpp_info.libs]))
        env.define("YDPDICT_CFLAGS", cflags)
        env.define("YDPDICT_LIBS", libs)
        tc.generate()
        # 适配要点 5：Autotools.configure() 走 conanfile.run(cmd)，无法传环境
        # 前缀，而 profile [buildenv] 的 SHELL/CONFIG_SHELL 会覆盖配方 env。
        # 暂存工具链参数，供 build() 自行以命令前缀方式调用 configure。
        self._ohc_configure_args = list(tc.configure_args)

    def build(self):
        apply_conandata_patches(self)
        # 适配要点 6：HMDFS 按目录“组位”授权，先放宽进程 umask。
        os.umask(0o002)
        shim_bin = os.path.join(self.build_folder, "shimbin")
        os.makedirs(shim_bin, exist_ok=True)
        shim_path = os.path.join(shim_bin, "mktemp")
        with open(shim_path, "w") as fh:
            fh.write(_MKTEMP_SHIM)
        os.chmod(shim_path, 0o755)
        os.environ["PATH"] = shim_bin + os.pathsep + os.environ.get("PATH", "")
        configure = os.path.join(self.source_folder, "configure")
        args = " ".join(getattr(self, "_ohc_configure_args", []))
        # 适配要点 9：依赖的 include/lib/pkgconfig 目录必须用命令前缀强制注入。
        # profile [buildenv] 里已有的 CPPFLAGS/LDFLAGS 会盖掉 generate() 中
        # env 注入的同名变量，导致 configure 的 AC_CHECK_HEADER([curses.h]) 与
        # AC_CHECK_LIB([ncursesw],[initscr]) 双双失败（-lncursesw 都找不到），
        # 最终 "checking for Unicode-aware ncurses... error: no"。
        nc = self.dependencies["ncurses"]
        nc_cpp = " ".join("-I" + d for d in nc.cpp_info.includedirs)
        nc_ld = " ".join("-L" + d for d in nc.cpp_info.libdirs)
        nc_pc = " ".join(os.path.join(d, "pkgconfig") for d in nc.cpp_info.libdirs)
        yd = self.dependencies["libydpdict"]
        yd_cpp = " ".join("-I" + d for d in yd.cpp_info.includedirs)
        yd_l = " ".join("-L" + d for d in yd.cpp_info.libdirs)
        yd_ld = " ".join([yd_l] + ["-l" + lib for lib in yd.cpp_info.libs])
        yd_pc = " ".join(os.path.join(d, "pkgconfig") for d in yd.cpp_info.libdirs)
        # 说明：-l 只进 YDPDICT_LIBS（链接行末尾），不进 LDFLAGS——静态库
        # 出现在目标文件之前会顺序错位导致 undefined reference。
        penv = (
            'PATH="{shim}:$PATH" SHELL=/bin/sh CONFIG_SHELL=/bin/sh '
            'CPPFLAGS="$CPPFLAGS {nc_cpp} {yd_cpp}" '
            'LDFLAGS="$LDFLAGS {nc_ld} {yd_l}" '
            'YDPDICT_CFLAGS="{yd_cpp}" YDPDICT_LIBS="{yd_ld}" '
            'PKG_CONFIG_PATH="$PKG_CONFIG_PATH:{nc_pc}:{yd_pc}"'
        ).format(shim=shim_bin, nc_cpp=nc_cpp, yd_cpp=yd_cpp, nc_ld=nc_ld,
                 yd_l=yd_l, yd_ld=yd_ld, nc_pc=nc_pc, yd_pc=yd_pc)
        self.run('{} "{}" {}'.format(penv, configure, args))
        make_program = self.conf.get("tools.gnu:make_program", default="make")
        self.run('{} "{}" -j1'.format(penv, make_program))

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
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_find_mode", "none")
