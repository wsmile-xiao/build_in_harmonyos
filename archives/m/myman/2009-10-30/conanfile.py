#!/usr/bin/env python3
"""Conan recipe — myman 2009-10-30 (Pac-Man 风格 X11/文本迷宫游戏)

构建单元提取（任务约束 2 的落实：不使用 imake/mxmkmf）:
- 上游 tarball 递归查找**无 Imakefile**（imake 预期不可用 → 实际不存在）。
  myman 2009-10-30 的构建系统三件套：
  1) 根 Makefile：5000+ 行 GNU Make 巨兽（自带字符串转义库、依赖 gsed/col/
     groff），把数据文件编译进二进制的机制走这里——OHOS/toybox 环境不可控；
  2) configure：676 行自定义 sh 脚本（非 autoconf），只把根 Makefile 拷成
     GNUmakefile + 探测 host，不生成编译配置，跳过；
  3) simple.mk：官方提供的简化构建（注释自述 "provided in case that is not
     possible"，Edit it to suit your configuration），编译单元明确。
  本配方按 simple.mk 提取编译单元，直接在 conan 配方中写编译命令：
    src/myman.c + src/utils.c + src/logic.c + mygetopt/mygetopt.c
    宏：-DXCURSES -DMYGETOPT；不定义 HAVE_CONFIG_H（走 inc/guess.h 特性
    推测；simple.mk 同款）；MY_CURSES_H=<xcurses.h>（myman.c XCURSES 分支）。
- X11 后端：myman 无原生 X11 代码，X11 显示 = PDCurses for X（XCurses，
  PDCurses 3.4 的 x11 端口，README: "(B) on an X Window System display
  (using PDCurses for X, a.k.a. XCurses)"）。PDCurses 3.4 自带 autotools
  configure；显式 --x-includes/--x-libraries 时 autoconf 跳过内部
  xmkmf/Imakefile 探测（configure 4464 行 case 分支），全程不碰 imake。
  只构建静态库 libXCurses.a（make 直接指定目标，绕开 MH_SHARED_LIBRARY
  2008 年共享库宏链）；xcurses.h 由 PDCurses 根 curses.h 拷贝改名（make
  install 的 sed 语义；curses.h 无 config.h 依赖，grep 实证）。

依赖（xeyes 1.3.1 同款策略）:
- conan 依赖（ohpcd 已发布 OHOS armv8 binary，W0 已 conan download 验证）：
  libx11/6.4.0 + libxext/6.4.0（transitive_headers/transitive_libs）
  + libxcb/1.16 + libxau/1.0.11（run=True，运行期 libX11.so.6 的 DT_NEEDED）。
- vendored X11 库（E277 模式，配方内从 X.Org 官方源按依赖序构建到 staging
  前缀）：PDCurses X11 端口链接 Xt/Xaw/Xmu/X11（x11.c grep 实证
  XawScrollbarSetThumb/XmuMakeAtom/XtAppAddTimeOut；无 XShm/Xext 符号调用）：
  xtrans 1.6.0（源码分发包头）→ libICE 1.1.1 → libSM 1.2.4 → libXt 1.2.1
  → libXmu 1.1.4 → libXpm 3.5.19 → libXaw 1.0.16（XAW7 的
  PKG_CHECK_MODULES 要求 xt xmu xpm；--disable-xaw6 跳过 XAW6 探测）。
- myman 运行期读数据文件（TILEFILE/SPRITEFILE/MAZEFILE 为文件名宏，默认
  chr/chr5x2.txt、spr/spr7x3.txt、lvl/maze.txt）：chr/ spr/ lvl/ 随包安装到
  share/myman/；sfx/ 不需要（SOUND 默认 0）。

测试:
- 上游无测试套件（根 Makefile/simple.mk 均无 test/check 目标，grep 实证）。
- test_package 无头真实执行被测二进制（R34）：myman -k 输出内置 MYMANKEYS
  "Keyboard Map" 后 exit(0)（utils.c:155/218，不初始化显示后端，Homebrew
  formula 同款测试路径）+ myman -L（legal notice）+ myman -h（usage）。

运行期共享库：vendored 6 库（libICE/libSM/libXt/libXmu 的 .so.6、
libXpm.so.4、libXaw.so.7）与 myman 同放 bin/，rpath $ORIGIN + SONAME 命名
（HMDFS symlink 物化不可靠 E050）；test_package 以 conanrun 环境
（LD_LIBRARY_PATH）+ LD_PRELOAD 绝对路径双保险注入 conan 依赖的
libX11/libXext 运行期库（libxau→libxdmcp→libxcb→libX11→libXext 依赖序）。
"""

import glob as _glob
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, get,
                               export_conandata_patches)
from conan.tools.layout import basic_layout


class MymanConan(ConanFile):
    name = "myman"
    version = "2009-10-30"
    description = "Text-mode/X11 videogame inspired by Namco's Pac-Man"
    license = "MIT"
    homepage = "https://myman.sourceforge.io/"
    url = "https://myman.sourceforge.io/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 链接库走 conan 依赖（libx11/6.4.0 + libxext/6.4.0，ohpcd 已发布
        # OHOS armv8 binary；xeyes/xclip/xsel 同款先例）。libxcb/libxau 为
        # 运行期传递依赖（libX11.so.6 的 DT_NEEDED），run=True 保证
        # test_package 的 conanrun 环境注入其 libdir。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        # xorgproto（xproto/xextproto/inputproto 等协议头，含 Xfuncproto.h/
        # Xos.h/Xatom.h）：vendored X11 库与 PDCurses 编译都需要；libx11 的
        # 传递依赖（ohpcd 已发布），显式声明保证 -I 目录可用（xeyes 靠
        # x11include/ 手工 vendor 40 个头，本配方走官方包，更干净）
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("libxcb/1.16", run=True)
        self.requires("libxau/1.0.11", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["myman"], strip_root=True)
        # vendored X11 依赖链 + PDCurses（E277 模式，xeyes 同款）
        for key, dst in (("pdcurses", "x11deps/PDCurses-3.4"),
                         ("libice", "x11deps/libICE"),
                         ("libsm", "x11deps/libSM"),
                         ("xtrans", "x11deps/xtrans"),
                         ("libxt", "x11deps/libXt"),
                         ("libxmu", "x11deps/libXmu"),
                         ("libxpm", "x11deps/libXpm"),
                         ("libxaw", "x11deps/libXaw")):
            get(self, **self.conan_data["sources"][key],
                strip_root=True, destination=dst)
        # xtrans 归档的 7 个实现文件位于归档根目录，而上游约定安装到
        # include/X11/Xtrans/（libICE/libSM 以 <X11/Xtrans/...> 引用），
        # 整理成 X11/Xtrans/ 子目录结构才能被 -I{x11deps}/xtrans 命中
        # （xeyes 同款）。
        _xtrans_root = os.path.join(self.source_folder, "x11deps", "xtrans")
        _xtrans_inc = os.path.join(_xtrans_root, "X11", "Xtrans")
        os.makedirs(_xtrans_inc, exist_ok=True)
        for _f in _glob.glob(os.path.join(_xtrans_root, "*.c")) + \
                  _glob.glob(os.path.join(_xtrans_root, "*.h")):
            os.rename(_f, os.path.join(_xtrans_inc, os.path.basename(_f)))

    # ------------------------------------------------------------------ helpers

    def _stage(self):
        return os.path.join(self.build_folder, "x11stage")

    def _dep_dirs(self, name):
        """取 conan 依赖包的 include/lib 目录（libx11/libxext/xorgproto）。

        xorgproto 为纯头包（libdirs 为空列表），lib 目录回退 "lib"。
        """
        dep = self.dependencies[name]
        inc = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
        libdirs = dep.cpp_info.libdirs or ["lib"]
        lib = os.path.join(dep.package_folder, libdirs[0])
        return inc, lib

    def _cc(self):
        """编译驱动器：取自 profile 的 tools.build:compiler_executables（R33：
        禁止 build() 依赖未定义的 shell 环境变量，不裸用 ${CC}）。"""
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            cc = compilers.get("c") or compilers.get("cpp")
        except Exception:  # noqa: BLE001
            cc = None
        return cc or os.environ.get("CC") or "clang"

    def _prepend_toolchain_path(self):
        """CI worker PATH 缺工具链目录（flint/3.6.0 同款，CI #27978）：clang
        按 conf 绝对路径可用但内部 ld.lld/as/nm 走 PATH → 前置工具链目录。
        幂等兜底，不影响真机路径（xeyes 同款実装）。"""
        cc = self._cc()
        toolchain_dir = os.path.dirname(cc)
        if not toolchain_dir:
            return
        cur = os.environ.get("PATH", "")
        if toolchain_dir in (cur.split(os.pathsep) if cur else []):
            return
        os.environ["PATH"] = toolchain_dir + os.pathsep + cur

    def _rewrite_configure(self):
        """HMDFS getcwd 兜底：改写 source_folder 下所有 configure 脚本
        （含 x11deps/ 下各 vendored 库 + PDCurses）的 pwd 判定与
        config.status 临时目录 umask（xeyes/nspr/aribb24 同款）；
        libXt 1.2.1 的 RAWCPP 遗留探针改走成功分支（xeyes 第 4 轮验证）。"""
        for _cfg in _glob.glob(os.path.join(self.source_folder, "**", "configure"),
                               recursive=True):
            try:
                with open(_cfg, "r", encoding="utf-8", errors="ignore") as _f:
                    _text = _f.read()
            except OSError:
                continue
            _orig = _text
            _text = _text.replace("umask 077", "umask 022")
            if "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&" in _text:
                _text = _text.replace(
                    "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&",
                    "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"\ntest -n \"$ac_pwd\" &&",
                    1)
            elif "if (pwd) >/dev/null 2>&1; then :; else" in _text:
                _text = _text.replace(
                    "if (pwd) >/dev/null 2>&1; then :; else",
                    "if (pwd) >/dev/null 2>&1 || test -n \"$PWD\"; then :; else")
            _rawcpp_unix = "if test `${RAWCPP} < conftest.$ac_ext | grep -c 'unix'` -eq 1 ; then"
            _rawcpp_pres = "if test `${RAWCPP} < conftest.$ac_ext | grep -c 'preserve   \\\"'` -eq 1 ; then"
            if _rawcpp_unix in _text:
                _text = _text.replace(_rawcpp_unix, "if test -n \"${RAWCPP}\" ; then")
            if _rawcpp_pres in _text:
                _text = _text.replace(_rawcpp_pres, "if test -n \"${RAWCPP}\" ; then")
            if _text != _orig:
                with open(_cfg, "w", encoding="utf-8") as _f:
                    _f.write(_text)

    def _build_vendored_lib(self, name, configure_args, extra_ldflags="",
                            extra_cppflags=""):
        """构建一个 vendored X11 库并 make install 到 staging 前缀。

        PKG_CHECK_MODULES 逃逸口：预置 <PREFIX>_CFLAGS/<PREFIX>_LIBS 跳过
        pkg-config（xeyes 同款机制）。各库 config.sub 均不支持 ohos 三元组
        且 2008-2012 年代 config.sub 不识别 aarch64，统一用
        --build/--host=x86_64-unknown-linux-gnu（E007 显式三元组跳过平台
        检测；双标相同=非交叉模式，conftest 在本机 OHOS aarch64 设备可运行）。
        rpath 通过环境变量 LDFLAGS 传入（`$$ORIGIN` 由 make 展开为 `$ORIGIN`）。
        """
        x11_inc, x11_lib = self._dep_dirs("libx11")
        _xext_inc, xext_lib = self._dep_dirs("libxext")
        xproto_inc, _ = self._dep_dirs("xorgproto")
        stage = self._stage()
        src = os.path.join(self.source_folder, "x11deps", name)
        os.environ["PWD"] = src
        os.environ["CPPFLAGS"] = (f"-I{x11_inc} -I{xproto_inc} "
                                  + extra_cppflags).strip()
        os.environ["LDFLAGS"] = (f"-L{x11_lib} -L{xext_lib} -L{stage}/lib "
                                 + extra_ldflags).strip()

        def _q(arg):
            name_, _, value = arg.partition("=")
            if " " in value or "'" in value:
                return name_ + "=" + shlex.quote(value)
            return arg

        cfg = (f"./configure --prefix={stage} "
               "--build=x86_64-unknown-linux-gnu --host=x86_64-unknown-linux-gnu "
               "--disable-docs --without-xmlto --without-fop --without-xsltproc "
               + " ".join(_q(a) for a in configure_args))
        self.run(cfg, cwd=src)
        self.run("make -j1", cwd=src)
        if str(self.settings.os) == "OHOS":
            shim = self._write_install_shim()
            self._redirect_install_to_shim(src, shim)
        self.run("make install", cwd=src)

    def _write_install_shim(self):
        """HMBS install shim 只接受单文件两参调用（多源批量 `install -c -m
        644 f1..fN dir/` 退出码 64=EX_USAGE，E182/E188）；写 cp/mkdir shim
        替代并重定向各库生成 Makefile 的 INSTALL（xeyes 同款，adms 2.3.7 /
        libgsf 1.14.58 / libICE 1.1.1 已过门禁）。"""
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "if [ \"$count\" -gt 1 ]; then\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then\n"
                    "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else\n"
                    "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                    "    fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:  # noqa: BLE001
            os.close(fd)
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        return install

    def _redirect_install_to_shim(self, root, shim_install):
        """把生成 Makefile 的 `INSTALL = <探测路径>/install` 替换为 shim
        （INSTALL_DATA/INSTALL_PROGRAM 引用 ${INSTALL} 自动重算，xeyes 同款）。"""
        for _root, _dirs, _files in os.walk(root):
            if "Makefile" not in _files:
                continue
            _mp = os.path.join(_root, "Makefile")
            try:
                with open(_mp, "r", encoding="utf-8", errors="ignore") as _f:
                    _content = _f.read()
            except OSError:
                continue
            if "INSTALL =" not in _content:
                continue
            _lines = []
            _changed = False
            for _line in _content.splitlines(True):
                _stripped = _line.lstrip()
                if _stripped.startswith("INSTALL = ") and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append(f"{_indent}INSTALL = {shim_install}\n")
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                with open(_mp, "w", encoding="utf-8") as _f:
                    _f.write("".join(_lines))

    def _materialize_stage_libs(self, libs):
        """把 staging 里各库的真实 .so 复制成常规名与 SONAME 名。

        -lXaw/-lXt/... 走 `-L{stage}/lib` 需要未版本化的 libX.so；下游
        DT_NEEDED（libXt.so.6 需要 libSM.so.6/libICE.so.6 等）按 SONAME 名
        解析。libtool make install 产出的是 symlink 链，HMFS 对 symlink
        物化不可靠（E050）；复制成实体文件（xeyes 同款，扩展 per-lib 版本）。
        """
        stage_lib = os.path.join(self._stage(), "lib")
        for lib, sover in libs:
            # libXaw 1.0.16 的产物命名特殊（libXaw7.so.7.0.0，SONAME 仍是
            # libXaw.so.7），glob 用 lib*.so* 兼容常规 libICE.so.6.3.0
            real = [p for p in _glob.glob(os.path.join(stage_lib, lib + "*.so*"))
                    if os.path.isfile(p) and not os.path.islink(p)]
            if not real:
                raise RuntimeError(f"vendored {lib} not installed to {stage_lib}")
            for plain in (lib + ".so", lib + ".so." + sover):
                dst = os.path.join(stage_lib, plain)
                if os.path.isfile(dst) and not os.path.islink(dst):
                    continue
                try:
                    os.unlink(dst)
                except OSError:
                    pass
                shutil.copy2(real[0], dst)

    def _sign_elf(self, path):
        """ELF 代码签名（OHOS 内核拒绝未签名 ELF，clinfo/xeyes 同款）。"""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    # -------------------------------------------------------------- build steps

    def _build_pdcurses(self):
        """PDCurses 3.4 X11 端口：configure 生成 config.h/Makefile 后只构建
        静态库 libXCurses.a（绕开 MH_SHARED_LIBRARY 共享库宏链），拷贝到
        staging，并把根 curses.h 拷为 xcurses.h（make install 的 sed 语义）。
        """
        x11_inc, x11_lib = self._dep_dirs("libx11")
        xext_inc, xext_lib = self._dep_dirs("libxext")
        xproto_inc, _ = self._dep_dirs("xorgproto")
        stage = self._stage()
        cc = self._cc()
        src = os.path.join(self.source_folder, "x11deps", "PDCurses-3.4")
        os.environ["PWD"] = src
        os.environ["CPPFLAGS"] = (f"-I{stage}/include -I{x11_inc} -I{xproto_inc} "
                                  f"-I{xext_inc}")
        os.environ["LDFLAGS"] = f"-L{stage}/lib -L{x11_lib} -L{xext_lib}"

        # --x-includes 支持空格分隔多目录（mh_inc_dirs 展开）；Intrinsic.h 在
        # stage/include（libXt 已安装），Xfuncproto.h/Xos.h 等在 xorgproto 包
        xinc_dirs = shlex.quote(f"{stage}/include {xproto_inc}")
        xlib_dirs = shlex.quote(f"{stage}/lib {x11_lib} {xext_lib}")
        cfg = (f"./configure --prefix={stage} "
               "--build=x86_64-unknown-linux-gnu --host=x86_64-unknown-linux-gnu "
               "--disable-option-check "
               f"--x-includes={xinc_dirs} --x-libraries={xlib_dirs} "
               f"CC={shlex.quote(cc)}")
        self.run(cfg, cwd=src)
        # configure 生成的 x11/Makefile 的 CPPFLAGS 只含 PDCurses 根 include
        # 与 MH_XINC_DIR（Intrinsic.h 所在目录）；configure 时的 env CPPFLAGS
        # 不写入 Makefile（x11/Makefile.in 的 CPPFLAGS 为固定定义），
        # Xlib.h/Xfuncproto.h 等来自 conan 依赖（libx11/xorgproto/libxext）
        # 的 include 目录需显式追加。PDCurses 源码用无前缀 include
        # （<keysym.h>/<Xatom.h>），故还需 x11_inc/xproto_inc 的 X11/
        # 子目录本身作为 -I 根（keysym.h 在 xorgproto 的 X11/ 下，
        # Xatom.h 在 libx11 的 X11/ 下；第 6 轮实测 keysym.h not found）。
        _mp = os.path.join(src, "x11", "Makefile")
        with open(_mp, "r", encoding="utf-8", errors="ignore") as _f:
            _mtext = _f.read()
        _extra = (f" -I{stage}/include -I{x11_inc} -I{xproto_inc} -I{xext_inc}"
                  f" -I{os.path.join(x11_inc, 'X11')}"
                  f" -I{os.path.join(xproto_inc, 'X11')}")
        if _extra not in _mtext:
            _mtext = re.sub(r"^(CPPFLAGS\s*=.*)$",
                            r"\1" + _extra, _mtext, count=1, flags=re.M)
            with open(_mp, "w", encoding="utf-8") as _f:
                _f.write(_mtext)
        # 静态库目标：x11/Makefile 的 `ar rv $@ $?`（PATH 已前置工具链，
        # /data/service/hnp/bin/ar 存在）；只取 .a，不碰 .so 目标
        self.run("make -C x11 libXCurses.a", cwd=src)
        copy(self, "libXCurses.a", os.path.join(src, "x11"),
             os.path.join(stage, "lib"))
        shutil.copy2(os.path.join(src, "curses.h"),
                     os.path.join(stage, "include", "xcurses.h"))

    def _build_myman(self):
        """myman 主程序：simple.mk 提取的编译单元 + -DXCURSES 手写编译链接。"""
        x11_inc, x11_lib = self._dep_dirs("libx11")
        xext_inc, xext_lib = self._dep_dirs("libxext")
        xproto_inc, _ = self._dep_dirs("xorgproto")
        stage = self._stage()
        cc = self._cc()
        src = self.source_folder
        objdir = os.path.join(self.build_folder, "myobjs")
        os.makedirs(objdir, exist_ok=True)
        opt = "-O0 -g" if str(self.settings.build_type) == "Debug" else "-O2"
        # MY_CURSES_H=<xcurses.h>（myman.c 的 XCURSES 分支）→ -I{stage}/include
        # 放最前；-DMYGETOPT 供 mygetopt/mygetopt.h；不定义 HAVE_CONFIG_H
        # （走 inc/guess.h 特性推测，simple.mk 同款，免配置）。
        # 编译器默认 target 即本机（OHOS aarch64，clang 绝对路径，无需
        # --target/--sysroot，xeyes/其他三方同款设备原生构建）。
        cppflags = (f"-DXCURSES -DMYGETOPT {opt} "
                    f"-Iinc -Imygetopt -I{stage}/include "
                    f"-I{x11_inc} -I{xproto_inc}")
        objs = []
        for src_rel, obj_name in (("src/myman.c", "myman.o"),
                                  ("src/utils.c", "utils.o"),
                                  ("src/logic.c", "logic.o"),
                                  ("mygetopt/mygetopt.c", "mygetopt.o")):
            obj = os.path.join(objdir, obj_name)
            self.run(f"{shlex.quote(cc)} -c {cppflags} -o {obj} {src_rel}",
                     cwd=src)
            objs.append(obj)
        # 链接序：静态 libXCurses.a 的未解析符号按序向后解析
        # （Xaw→Xmu→Xt→Xpm→SM→ICE→Xext→X11）；-lm 供 PDCurses 可能用到的
        # 数学符号（libm 在 OHOS musl 为薄层，无害）。
        link = (f"{shlex.quote(cc)} {' '.join(objs)} "
                f"-o {os.path.join(objdir, 'myman')} "
                f"-L{stage}/lib -L{x11_lib} -L{xext_lib} "
                "-lXCurses -lXaw -lXmu -lXt -lXpm -lSM -lICE -lXext -lX11 -lm "
                "-Wl,-rpath,'$ORIGIN'")
        self.run(link, cwd=src)

    def build(self):
        # 应用 myman.c 的 XCurses argc/argv 修复补丁（patches/0001）
        apply_conandata_patches(self)
        # CI worker PATH 缺工具链目录（flint/3.6.0 同款）：先补 PATH。
        self._prepend_toolchain_path()
        # HMDFS: conan 缓存父目录对 getcwd() 不可达，进程 cwd 固定到
        # build_folder 并预置 PWD（xeyes 同款）。
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder
        # 改写 source_folder 下所有 configure（6 库 + PDCurses）的 pwd 判定
        # 与 umask；libXt 的 RAWCPP 探针在此一并处理。
        self._rewrite_configure()

        x11_inc, x11_lib = self._dep_dirs("libx11")
        xext_inc, xext_lib = self._dep_dirs("libxext")
        xproto_inc, _ = self._dep_dirs("xorgproto")
        stage = self._stage()
        xtrans_inc = os.path.join(self.source_folder, "x11deps", "xtrans")

        # vendored X11 库（xeyes 1.3.1 已验证同款构建路径，按依赖序）
        # libICE 1.1.1: 逃逸 ICE_CFLAGS/ICE_LIBS（xproto >= 7.0.25 xtrans）；
        # icetrans.c 直接 #include <X11/Xtrans/transport.c>（xtrans 源码头）
        self._build_vendored_lib("libICE", [
            "ICE_CFLAGS=-I{xtrans} -I{xproto} -I{x11}".format(
                xtrans=xtrans_inc, xproto=xproto_inc, x11=x11_inc),
            "ICE_LIBS=-L{x11}".format(x11=x11_lib),
        ], extra_cppflags=f"-I{xtrans_inc}")
        self._materialize_stage_libs([("libICE", "6")])
        # libSM 1.2.4: sm_manager.c 引用 Xtrans.h；链接 staging 的 libICE
        self._build_vendored_lib("libSM", [
            "SM_CFLAGS=-I{stage}/include -I{xtrans} -I{xproto} -I{x11}".format(
                stage=stage, xtrans=xtrans_inc, xproto=xproto_inc, x11=x11_inc),
            "SM_LIBS=-L{stage}/lib -L{x11} -lICE".format(
                stage=stage, x11=x11_lib),
        ], extra_cppflags=f"-I{xtrans_inc}",
            extra_ldflags="-Wl,-rpath,'$$ORIGIN'")
        self._materialize_stage_libs([("libSM", "6")])
        # libXt 1.2.1: -lSM/-lICE 指向 staging；RAWCPP 探针已由
        # _rewrite_configure 改写走成功分支
        self._build_vendored_lib("libXt", [
            "XT_CFLAGS=-I{stage}/include -I{xproto} -I{x11}".format(
                stage=stage, xproto=xproto_inc, x11=x11_inc),
            "XT_LIBS=-L{stage}/lib -L{x11} -lSM -lICE -lX11".format(
                stage=stage, x11=x11_lib),
        ], extra_ldflags="-Wl,-rpath,'$$ORIGIN'")
        self._materialize_stage_libs([("libXt", "6")])
        # libXmu 1.1.4: -I/-l 需含 staging 的 libXt 头与库；ShapeWidg.c 引用
        # <X11/extensions/shape.h>（在 libxext 包的 include，xeyes 靠 vendor
        # 头，本配方直接从 conan libxext 取）
        self._build_vendored_lib("libXmu", [
            "XMU_CFLAGS=-I{stage}/include -I{xproto} -I{x11} -I{xext}".format(
                stage=stage, xproto=xproto_inc, x11=x11_inc, xext=xext_inc),
            "XMU_LIBS=-L{stage}/lib -L{x11} -L{xext} -lXt -lXext -lX11".format(
                stage=stage, x11=x11_lib, xext=xext_lib),
            "XMUU_CFLAGS=-I{xproto} -I{x11}".format(
                xproto=xproto_inc, x11=x11_inc),
            "XMUU_LIBS=-L{x11} -lX11".format(x11=x11_lib),
        ], extra_ldflags="-Wl,-rpath,'$$ORIGIN'")
        self._materialize_stage_libs([("libXmu", "6")])
        # libXpm 3.5.19: SXPM（sxpm 工具）探测带 action-if-not-found，失败
        # 自动禁用，无需逃逸；XPM 必须逃逸（xproto x11）
        self._build_vendored_lib("libXpm", [
            "XPM_CFLAGS=-I{xproto} -I{x11}".format(
                xproto=xproto_inc, x11=x11_inc),
            "XPM_LIBS=-L{x11} -lX11".format(x11=x11_lib),
        ], extra_ldflags="-Wl,-rpath,'$$ORIGIN'")
        self._materialize_stage_libs([("libXpm", "4")])
        # libXaw 1.0.16: --disable-xaw6 跳过 XAW6 探测只建 libXaw.so.7；
        # XAW7 + 公共 XPM 探测逃逸（configure.ac 27/87/88 行）
        self._build_vendored_lib("libXaw", [
            "--disable-xaw6",
            "XAW7_CFLAGS=-I{stage}/include -I{xproto} -I{x11} -I{xext}".format(
                stage=stage, xproto=xproto_inc, x11=x11_inc, xext=xext_inc),
            "XAW7_LIBS=-L{stage}/lib -L{x11} -L{xext} -lXmu -lXt -lXpm -lXext -lX11".format(
                stage=stage, x11=x11_lib, xext=xext_lib),
            "XPM_CFLAGS=-I{xproto} -I{x11}".format(
                xproto=xproto_inc, x11=x11_inc),
            "XPM_LIBS=-L{x11} -lX11".format(x11=x11_lib),
        ], extra_ldflags="-Wl,-rpath,'$$ORIGIN'")
        self._materialize_stage_libs([("libXaw", "7")])

        # PDCurses 3.4 → libXCurses.a（X 显示后端）
        self._build_pdcurses()
        # myman 主程序（simple.mk 提取编译单元）
        self._build_myman()

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "myman", os.path.join(self.build_folder, "myobjs"), bin_dir)
        # 内建的 6 个 X11 库（SONAME 命名）复制到 bin/ 与 myman 同目录，
        # rpath $ORIGIN 同目录寻库（xeyes 同款做法；HMDFS 不跟踪 symlink
        # E050，跨 staging 时直接拷实体文件并改名 SONAME）。
        stage = self._stage()
        for lib, sover in (("libICE", "6"), ("libSM", "6"), ("libXt", "6"),
                           ("libXmu", "6"), ("libXpm", "4"), ("libXaw", "7")):
            real = [p for p in _glob.glob(os.path.join(stage, "lib", lib + "*.so*"))
                    if os.path.isfile(p) and not os.path.islink(p)]
            if not real:
                raise RuntimeError(f"vendored {lib} not found in {stage}/lib")
            src = real[0]
            copy(self, os.path.basename(src), os.path.dirname(src), bin_dir)
            dst = os.path.join(bin_dir, os.path.basename(src))
            os.rename(dst, os.path.join(bin_dir, lib + ".so." + sover))
        # 游戏数据文件（运行期读取，TILEFILE/SPRITEFILE/MAZEFILE 文件名宏）
        for d in ("chr", "spr", "lvl"):
            copy(self, "*", os.path.join(self.source_folder, d),
                 os.path.join(self.package_folder, "share", "myman", d))
        # OHOS ELF 签名（拒绝未签名可执行文件）
        for f in os.listdir(bin_dir):
            self._sign_elf(os.path.join(bin_dir, f))

    def package_info(self):
        # 命令行工具：仅提供 bin/（R38）
        self.cpp_info.bindirs = ["bin"]
        # 内建 X11 库与 myman 同在 bin/：声明 libdirs 让 test_package 的
        # conanrun 环境把 <pkg>/bin 加入 LD_LIBRARY_PATH（xeyes 同款兜底）
        self.cpp_info.libdirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []