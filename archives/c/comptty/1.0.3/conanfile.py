#!/usr/bin/env python3
"""Conan recipe for comptty 1.0.3 — Autotools (C++ FLTK GUI 应用).

comptty 是 W1HKJ（fldigi/flrig/comptext 同作者）的 FLTK GUI 应用，用于比较
两个 RTTY 数据流，计算字符错误率（CER）与比特错误率（BER）。X11 后端，
硬依赖 libfltk（API 1.1/1.3，由 libfltk/1.3.11 静态库提供）。

OHOS 适配要点（本地编译实证，见 notes.md）:
- 官方 GitHub tag tarball 不含 configure 脚本（仅 configure.ac + 已生成
  aclocal.m4/Makefile.in/config.h.in）：build() 先用 autoconf 生成 configure
- config.guess 2008 版不识别 HarmonyOS（uname -s=HarmonyOS）：0001 补丁添加
  aarch64-HarmonyOS 分支映射为 aarch64-unknown-linux-gnu（comptext 已合入
  同款方案，最小补丁不动 config.sub）
- 官方 tarball 的 build-aux/compile 是绝对路径符号链接（指向
  /usr/share/automake-1.15/compile，CI 环境不存在）：source() 中用 Python
  直接替换为真实 compile 脚本（GNU patch 无法应用符号链接→文件补丁，
  实测 FileNotFoundError），否则 configure 报 "cannot find required
  auxiliary files: compile"
- configure: autoconf 生成的 config.status 用 mktemp -d + umask 077——
  HMDFS 上 0700 目录属主映射为 file_manager，进程 euid 无法写入导致
  "Permission denied"（E011）；build() 生成 configure 后 sed umask 077→022
- FLTK_CFLAGS/FLTK_LIBS 手动注入：configure.ac 检测到两者已设即跳过
  fltk-config 检查（fltk-config 引用的 .cache 路径为 CI 构建残留，本地不可用）
- LD_LIBRARY_PATH 注入全部依赖 lib + OHOS SDK llvm/lib（libc++_shared.so，
  configure conftest 运行时必需，CI profile 同款配置）
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# automake 标准 compile wrapper（build-aux/compile 真实内容）。
# 上游 tarball 中该文件是绝对路径符号链接（-> /usr/share/automake-1.15/compile），
# CI 环境目标不存在，source() 中用它替换符号链接。
_COMPILE_WRAPPER = r'''#! /bin/sh
# Wrapper for compilers which do not understand '-c -o'.
scriptversion=2018-03-07.03; # UTC

case $1 in
  '')
     echo "$0: No command.  Try '$0 --help' for more information." 1>&2
     exit 1;
     ;;
  -h | --h*)
    cat <<\EOF
Usage: compile [--help] [--version] PROGRAM [ARGS]
Wrapper for compilers which do not understand '-c -o'.
Report bugs to <bug-automake@gnu.org>.
EOF
    exit $?
    ;;
  -v | --v*)
    echo "compile $scriptversion"
    exit $?
    ;;
esac

ofile=
cfile=
eat=

for arg
do
  if test -n "$eat"; then
    eat=
  else
    case $1 in
      -o)
	ofile=$2
	shift
	;;
      *.c)
	cfile=$1
	shift
	;;
      *)
	set -- "$@" "$1"
	shift
	;;
    esac
  fi
done

if test -z "$ofile" || test -z "$cfile"; then
  exec "$@"
fi

cofile=`echo "$cfile" | sed 's|^.*[\\/]||; s|^[a-zA-Z]:||; s/\.c$/.o/'`
exec "$@"
'''


class CompttyConan(ConanFile):
    name = "comptty"
    version = "1.0.3"
    description = "comptty — compare two RTTY streams, compute BER and CER (W1HKJ ham radio family)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/w1hkj/comptty"
    url = "https://github.com/w1hkj/comptty"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # 官方 tarball 无 configure（git archive 不含 autotools 生成物），
        # 需 autoconf 自举生成。不用 tool_requires("autoconf/2.72")：
        # 其依赖 perl 包的 Cwd.so 在 HMDFS 上无执行权限无法加载
        # （实测 "Permission denied ... Cwd.so"）。CI 系统路径
        # /data/service/hnp/bin 已有 autoconf 家族（abiword 先例注释确认），
        # 由 profile buildenv PATH 注入，build() 用完整路径调用。
        pass

    def requirements(self):
        # FLTK 静态库（含 libx11/1.8.13 传递依赖）
        self.requires("libfltk/1.3.11")
        # xorgproto 提供 X11/X.h 协议头（Xlib.h 内部 #include <X11/X.h>）。
        # 作为传递依赖会被 conan 标为 "Skipped binaries" 不装头文件（编译
        # 实测 fatal error: 'X11/X.h' file not found），提升为直接 requires
        # 强制安装（libfltk 已合入配方同款修复，hyprpicker 传递依赖先例）
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游 tarball 的 build-aux/compile 是绝对路径符号链接
        # （-> /usr/share/automake-1.15/compile，CI 环境不存在，导致
        #  configure 报 "cannot find required auxiliary files: compile"）。
        # GNU patch 无法应用符号链接→普通文件的补丁（实测 FileNotFoundError），
        # 故在 source() 中用 Python 直接替换为真实的 automake compile wrapper。
        _compile = os.path.join(self.source_folder, "build-aux", "compile")
        if os.path.islink(_compile):
            os.remove(_compile)
            with open(_compile, "w") as _f:
                _f.write(_COMPILE_WRAPPER)
            os.chmod(_compile, 0o755)
        # 上游 tarball 自带的 src/config.h 是过期生成物（VERSION="1.0.2"，
        # 见 v1.0.3 tag 核查）。VPATH 构建中 main.cxx 的 #include "config.h"
        # 引号形式优先搜索源文件所在目录（source_folder/src/config.h），
        # 导致编译用过期头、二进制 --version 输出版本号错误（实测 1.0.2）。
        # configure 的 AC_CONFIG_HEADERS 会在 build 目录重新生成 config.h，
        # 删除残留后即可正确 fallback 到新生成的头。
        _stale_config_h = os.path.join(self.source_folder, "src", "config.h")
        if os.path.isfile(_stale_config_h):
            os.remove(_stale_config_h)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        env = tc.environment()

        # 依赖 include/lib 路径手动注入（不用 AutotoolsDeps：其会把依赖
        # -l 全塞进 LIBS，configure 早期 conftest 链上依赖找不到 .so；
        # qalculate-gtk / comptext 已合入同款做法）
        for _ref, _dep in self.dependencies.items():
            _inc = " ".join("-I{}".format(_d)
                            for _d in (_dep.cpp_info.includedirs or [])
                            if os.path.isabs(_d))
            if _inc:
                env.prepend("CPPFLAGS", _inc)
                env.prepend("CXXFLAGS", _inc)
                env.prepend("CFLAGS", _inc)
            _lp = " ".join("-L{}".format(_d)
                           for _d in (_dep.cpp_info.libdirs or [])
                           if os.path.isabs(_d))
            if _lp:
                env.prepend("LDFLAGS", _lp)

        # FLTK_CFLAGS/FLTK_LIBS：configure.ac 检测到两者已设即跳过
        # fltk-config 检查（fltk-config 引用的 .cache 路径为 CI 残留不可用）
        fltk = self.dependencies["libfltk"]
        x11 = self.dependencies["libx11"]
        _fltk_inc = "-I{}".format(os.path.join(fltk.package_folder, "include"))
        _x11_inc = "-isystem{}".format(os.path.join(x11.package_folder, "include"))
        _extra_inc = ""
        # xorgproto 提供 X11/X.h 协议头（Xlib.h 内部 include）；作为传递
        # 依赖可能被 conan 标为 "Skipped binaries"（无 package_folder），
        # 空值保护（libfltk 已合入配方同款处理）
        xorg = self.dependencies.get("xorgproto")
        if xorg and xorg.package_folder:
            _extra_inc = " -isystem{}".format(
                os.path.join(xorg.package_folder, "include"))
        env.define("FLTK_CFLAGS", "{}{}{}".format(
            _fltk_inc, _x11_inc, _extra_inc))
        env.define("FLTK_LIBS",
                   "-L{} -lfltk_images -lfltk -lm -lX11 -lpthread -ldl".format(
                       os.path.join(fltk.package_folder, "lib")))

        # PKG_CONFIG_PATH：configure.ac 的 X11 检测（PKG_CHECK x11）需要
        pc_dirs = []
        for _dep in self.dependencies.values():
            # 被 conan 标为 "Skipped binaries" 的传递依赖无 package_folder，
            # 空值保护（同 xorgproto 处理）
            if not _dep.package_folder:
                continue
            for _sub in ("lib/pkgconfig", "share/pkgconfig"):
                _d = os.path.join(_dep.package_folder, _sub)
                if os.path.isdir(_d):
                    pc_dirs.append(_d)
        if pc_dirs:
            env.prepend_path("PKG_CONFIG_PATH", os.pathsep.join(pc_dirs))

        # LD_LIBRARY_PATH：configure conftest 运行时需要 libX11.so.6 及
        # 其传递库（libxcb/libXau/libXdmcp）+ libc++_shared.so（OHOS llvm）。
        # 受控实验（2026-09-10）：libc++_shared.so 位于 llvm/lib 的
        # aarch64-linux-ohos 子目录，该子目录必须**置前**——仅 append 到
        # 末尾时 conftest 报 "Error loading shared library libc++_shared.so"
        # （loader 搜索到前置的 llvm/lib 等目录后异常终止，未继续搜到子目录）；
        # prepend 置前（实验 3）运行 OK。
        lib_paths = [
            os.path.join(_dep.package_folder, "lib")
            for _dep in self.dependencies.values()
            if _dep.package_folder
            and os.path.isdir(os.path.join(_dep.package_folder, "lib"))
        ]
        if lib_paths:
            env.append_path("LD_LIBRARY_PATH", os.pathsep.join(lib_paths))
        llvm_lib = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                    "ohos/native/llvm/lib/aarch64-linux-ohos")
        if os.path.isdir(llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)

        tc.generate(env)

    def build(self):
        # 官方 tarball 无 configure（仅 configure.ac），先 autoconf 生成；
        # 生成后 sed umask 077→022（E011：HMDFS 上 0700 临时目录不可写）。
        # autoconf 用系统完整路径（tool_requires 的 perl 依赖在 HMDFS 上
        # Cwd.so 无执行权限，实测报错；/data/service/hnp/bin 由 profile
        # buildenv PATH 注入，CI 同款）
        autoconf_bin = "/data/service/hnp/bin/autoconf"
        self.run("{}".format(autoconf_bin), cwd=self.source_folder)
        self.run("sed -i 's/umask 077/umask 022/g' configure",
                 cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS 不支持 make jobserver（mkfifo 被拒），强制 -j1
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI 应用（R38：软件级 commands.json 声明 tool）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        # 运行期依赖 libc++_shared.so（OHOS llvm，aarch64-linux-ohos 子目录）
        # 与 libX11 传递库，注入 runenv 使 test_package/下游可运行二进制
        # （不注入则 conanrun 环境缺路径，comptty --version 报 rc=127）
        _llvm_lib = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                     "ohos/native/llvm/lib/aarch64-linux-ohos")
        if os.path.isdir(_llvm_lib):
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
