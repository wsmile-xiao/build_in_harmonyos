#!/usr/bin/env python3
"""Conan recipe — xeyes 1.3.1 (X11 眼球跟踪演示程序)

Build system: autotools (configure + make)
License: MIT
Homepage: https://gitlab.freedesktop.org/xorg/app/xeyes

依赖说明: X11 链接库（libX11/libXext）来自 conan 依赖 libx11/6.4.0 +
libxext/6.4.0（ohpcd 已发布 OHOS armv8 binary，xclip/xsel/libxscrnsaver
同款先例），不再依赖编译环境预编译栈 /storage/Users/currentUser/usr/local
（CI worker 的栈可能完全没有 libX11，CI #28097 实测 "no libX11.so /
libX11.so.* / libX11.a"）。libXi/libXt/libXmu/libSM/libICE 五个库仍按
E277 vendored 依赖模式 + 经验 1（clinfo 内建 OpenCL-ICD-Loader）先例，
配方内从 X.Org 官方源按依赖序构建到 staging 前缀
（build_folder/x11stage）：libICE → libSM → libXt（libXt 链接 -lSM
-lICE），libXi/libXmu 随后；libICE/libSM 编译引用
<X11/Xtrans/...>，故同时内建 xtrans 源码头（X11/Xtrans/ 布局）。
xeyes 链接这些库并以 rpath $ORIGIN + SONAME 打包进 bin/，最后用
binary-sign-tool 自签（OHOS 内核拒绝未签名 ELF）。
- libICE 1.1.1（Inter-Client Exchange，libSM/libXt 的传递依赖）
- libSM 1.2.4（Session Management，libXt 链接 -lSM）
- libXt 1.2.1（Xt widget 工具库，xeyes 的 XtAppInitialize 依赖）
- libXi 1.8.1（XInput2 扩展，Eyes.c 的 XIQueryVersion/XISelectEvents）
- libXmu 1.1.4（Xmu 工具库，xeyes 的 XmuCvtStringToBackingStore）
- xtrans 1.6.0（源码分发包：Xtrans.h/transport.c 等，libICE/libSM 引用）

上游无测试套件：Makefile.am 无 check/TESTS 目标、meson.build 无 test()、
源码包无 test/ 目录或测试文件（审计见 test_package/MANIFEST.yml）。
test_package 以 xeyes -version/-help（无需 X server，在 XtAppInitialize
之前退出）真实执行被测二进制。

运行期依赖（第 4 轮真机根因）：conan libx11 的 libX11.so.6 运行时
DT_NEEDED 需要 libxcb.so.1/libXau.so.6；配方以 conan run 依赖
（libxcb/1.16 + libxau/1.0.11，ohpcd 已发布 OHOS armv8 binary）补齐，
test_package 用 LD_PRELOAD 绝对路径注入测试命令。
"""
import glob as _glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XeyesConan(ConanFile):
    name = "xeyes"
    version = "1.3.1"
    description = "A follow the mouse X demo, using the X SHAPE extension"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xeyes"
    url = "https://gitlab.freedesktop.org/xorg/app/xeyes"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # vendor 的 X11 头文件（libXt/libXmu/libXext/libXi/libXfixes/SM/ICE）
        # 复制到 export_sources，供 generate()/build() 使用（abook 同款用法）
        _src = os.path.join(self.recipe_folder, "x11include")
        _dst = os.path.join(self.export_sources_folder, "x11include")
        if os.path.isdir(_src) and not os.path.exists(_dst):
            shutil.copytree(_src, _dst)

    def requirements(self):
        # X11 链接库改为 conan 依赖（libx11/6.4.0 + libxext/6.4.0，ohpcd 已
        # 发布 OHOS armv8 binary；xclip/xsel/libxscrnsaver 同款先例）。不再依赖
        # 编译环境预编译栈 /storage/Users/currentUser/usr/local：CI worker 的
        # 栈可能完全没有 libX11（CI #28097 worker CI-018 实测
        # "no libX11.so / libX11.so.* / libX11.a"，_materialize_sys_libs 抛错），
        # 栈内任何形态的库都不保证存在。libx11 传递依赖 libxcb/1.16 +
        # libxau/1.0.11（运行期 libX11.so.6 的 DT_NEEDED，且 libxcb 传递依赖
        # libxdmcp/1.1.5），显式声明 run=True 保证 test_package 的 conanrun
        # 环境注入其 libdir（LD_LIBRARY_PATH），配合 LD_PRELOAD 兜底
        # （HMBS [stale_runtime_library]）。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxcb/1.16", run=True)
        self.requires("libxau/1.0.11", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["xeyes"], strip_root=True)
        # vendored X11 依赖库：真机栈缺失，需从官方源构建（E277 模式）。
        # libXt 链接依赖 libSM/libICE（栈同样没有这两个库，见 XT_LIBS
        # 逃逸注释），libSM 又依赖 libICE；libICE/libSM 的源码直接引用
        # <X11/Xtrans/...>（icetrans.c 甚至 #include transport.c），因此
        # 还需 xtrans 源码包（仓库 xtrans/1.6.0 配方同款官方源）。
        for key, dst in (("libice", "x11deps/libICE"),
                         ("libsm", "x11deps/libSM"),
                         ("xtrans", "x11deps/xtrans"),
                         ("libxt", "x11deps/libXt"),
                         ("libxi", "x11deps/libXi"),
                         ("libxmu", "x11deps/libXmu")):
            get(self, **self.conan_data["sources"][key],
                strip_root=True, destination=dst)
        # xtrans 归档的 7 个实现文件（Xtrans.h/Xtrans.c/Xtransint.h/
        # Xtranslcl.c/Xtranssock.c/Xtransutil.c/transport.c）位于归档根目录，
        # 而上游约定安装到 include/X11/Xtrans/（仓库 xtrans/1.6.0 配方
        # package() 同款布局）；libICE/libSM 以 <X11/Xtrans/...> 方式引用，
        # 需整理成 X11/Xtrans/ 子目录结构才能被 -I{x11deps}/xtrans 命中。
        _xtrans_root = os.path.join(self.source_folder, "x11deps", "xtrans")
        _xtrans_inc = os.path.join(_xtrans_root, "X11", "Xtrans")
        os.makedirs(_xtrans_inc, exist_ok=True)
        for _f in _glob.glob(os.path.join(_xtrans_root, "*.c")) + \
                  _glob.glob(os.path.join(_xtrans_root, "*.h")):
            os.rename(_f, os.path.join(_xtrans_inc, os.path.basename(_f)))

    def generate(self):
        tc = AutotoolsToolchain(self)
        # X11 链接库/头文件来自 conan 依赖（libx11/6.4.0 + libxext/6.4.0，
        # ohpcd 已发布；xclip/xsel/libxscrnsaver 同款）。不再依赖编译环境
        # 预编译栈（CI worker 的栈可能完全没有 libX11，见 requirements 注释）。
        x11_inc, x11_lib = self._dep_dirs("libx11")
        xext_inc, xext_lib = self._dep_dirs("libxext")
        tc.configure_args.append(f"--x-includes={x11_inc}")
        tc.configure_args.append(f"--x-libraries={x11_lib}")
        # 交叉编译模式（跳过 configure 运行时检测，E007 修复）
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # PKG_CHECK_MODULES 需要 pkg-config 找到 xi/x11/xt/xext/xmu/xproto 的 .pc
        pkg_cfg = os.path.join(x11_lib, "pkgconfig")
        existing = os.environ.get("PKG_CONFIG_PATH", "").strip()
        if existing:
            pkg_cfg = pkg_cfg + ":" + existing
        tc.configure_args.append(f"PKG_CONFIG_PATH={pkg_cfg}")
        # conan 包（libx11/libxext）未随附全部 .pc 文件（libx11 包只有 x11.pc，
        # xi/xt/xmu 等 .pc 需各自库包；xclip 同款）。configure 的
        # PKG_CHECK_MODULES 提供文档化逃逸口：预置 XEYES_CFLAGS/XEYES_LIBS
        # 后直接采用、不再调用 pkg-config（adcli KRB5_CFLAGS/KRB5_LIBS、
        # coturn SSL_CFLAGS/SSL_LIBS 同款先例）。xeyes 实际链接
        # Xi/X11/Xt/Xext/Xmu（Eyes.c: XInput2/XShape，xeyes.c: Xt）。
        # 三个库由配方内建到 staging（build_folder/x11stage），链接时
        # -L 前置 staging 再回落 conan 依赖；-DXTSTRINGDEFINES 让 StringDefs.h/
        # Shell.h 走字符串字面量分支，不依赖 libXt.so 导出的 XtStrings[]
        # 偏移（规避 .so 版本差异）。
        vendor_inc = os.path.join(self.source_folder, "x11include")
        stage_inc = os.path.join(self._stage(), "include")
        tc.configure_args.append(
            f"XEYES_CFLAGS=-I{stage_inc} -I{vendor_inc} -I{x11_inc} -I{xext_inc} -DXTSTRINGDEFINES")
        tc.configure_args.append(
            f"XEYES_LIBS=-L{self._stage()}/lib -L{x11_lib} -L{xext_lib} -lXi -lX11 -lXt -lXext -lXmu")
        # xrender/present 为可选特性：configure 默认 try 语义下
        # PKG_CHECK_MODULES 缺包即硬失败，按 .pc 文件探测决定启用/关闭
        if not os.path.isfile(os.path.join(pkg_cfg.split(":")[0], "xrender.pc")):
            tc.configure_args.append("--with-xrender=no")
        if not os.path.isfile(os.path.join(pkg_cfg.split(":")[0], "xcb-present.pc")):
            tc.configure_args.append("--with-present=no")
        # 确保 configure 测试程序能链接 X11 库
        tc.extra_ldflags.append(f"-L{x11_lib}")
        tc.extra_ldflags.append(f"-L{xext_lib}")
        tc.generate()

    def _stage(self):
        return os.path.join(self.build_folder, "x11stage")

    def _dep_dirs(self, name):
        """取 conan 依赖包的 include/lib 目录（libx11/libxext，ohpcd 已发布）。

        xclip/xsel 同款：直接访问依赖包 package_folder 下的 cpp_info 目录，
        不依赖编译环境预编译栈（CI worker 的栈可能完全没有 libX11）。
        """
        dep = self.dependencies[name]
        inc = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
        lib = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        return inc, lib

    def _prepend_toolchain_path(self):
        """CI worker PATH 缺工具链目录（flint/3.6.0 同款，CI #27978 实测）：
        clang 按 tools.build:compiler_executables conf 的绝对路径被找到
        （/data/service/hnp/bin/clang），但 clang 内部调用的 ld.lld/as/nm
        走 PATH 解析 → configure 报 "C compiler cannot create executables"。
        从编译器路径 dirname 推导工具链目录并前置到 PATH（不硬编码机器
        路径）；已在 PATH 前缀则跳过。真机 hmbs 预检会注入工具目录，此
        处为幂等兜底，不影响真机路径。
        """
        cc = None
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            cc = compilers.get("c") or compilers.get("cpp")
        except Exception:
            cc = None
        if not cc:
            cc = os.environ.get("CC")
        if not cc:
            return
        toolchain_dir = os.path.dirname(cc)
        if not toolchain_dir:
            return
        cur = os.environ.get("PATH", "")
        if toolchain_dir in (cur.split(os.pathsep) if cur else []):
            return
        os.environ["PATH"] = toolchain_dir + os.pathsep + cur

    def _rewrite_configure(self):
        """HMDFS getcwd 兜底：改写 source_folder 下所有 configure 脚本。

        conan 缓存父目录对 getcwd() 不可达（build 目录存在、路径查找可用，
        但 getcwd() 沿父链上溯失败），configure 顶部 `pwd` 判定直接报
        "working directory cannot be determined"。改写为 pwd 失败时回退
        $PWD（与 nspr/aribb24/libgsf 同款）；同时把 config.status 临时
        目录创建处 umask 077 → 022（E114/E129）。递归 glob 一并覆盖
        x11deps/ 下三个 vendored 库的 configure 脚本。
        """
        for _cfg in _glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
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
                    1,
                )
            elif "if (pwd) >/dev/null 2>&1; then :; else" in _text:
                _text = _text.replace(
                    "if (pwd) >/dev/null 2>&1; then :; else",
                    "if (pwd) >/dev/null 2>&1 || test -n \"$PWD\"; then :; else",
                )
            # libXt 1.2.1 的 XORG_PROG_RAWCPP 遗留探针（Imake 时代产物）：
            # `clang < conftest | grep -c 'unix'`。在 OHOS 工具链上 RAWCPP
            # 解析为 /data/service/hnp/bin/clang，被当作编译驱动（无 -E、无
            # 位置输入文件）运行，重定向 stdin 不作输入 → `clang: error: no
            # input files`，三路探针全失败 → configure abort "defines unix
            # with or without -undef"。RAWCPP/RAWCPPFLAGS 在整个 libXt 构建
            # 中无任何消费点（StringDefs.h/Shell.h/StringDefs.c 由
            # util/makestrs 生成，见 src/Makefile.in:993），故强制探针走
            # "无需 -undef/-traditional" 成功分支（置空 RAWCPPFLAGS，与
            # 常规 GCC 系统返回值一致）是安全的。
            _rawcpp_unix = "if test `${RAWCPP} < conftest.$ac_ext | grep -c 'unix'` -eq 1 ; then"
            _rawcpp_pres = "if test `${RAWCPP} < conftest.$ac_ext | grep -c 'preserve   \\\"'` -eq 1 ; then"
            if _rawcpp_unix in _text:
                _text = _text.replace(_rawcpp_unix, "if test -n \"${RAWCPP}\" ; then")
            if _rawcpp_pres in _text:
                _text = _text.replace(_rawcpp_pres, "if test -n \"${RAWCPP}\" ; then")
            if _text != _orig:
                with open(_cfg, "w", encoding="utf-8") as _f:
                    _f.write(_text)

    def _build_vendored_lib(self, name, configure_args, extra_ldflags="", extra_cppflags=""):
        """构建一个 vendored X11 库并 make install 到 staging 前缀。

        使用 PKG_CHECK_MODULES 逃逸口：预置 <PREFIX>_CFLAGS/<PREFIX>_LIBS
        跳过 pkg-config（与 xeyes 的 XEYES_CFLAGS/XEYES_LIBS 同机制）。
        各库的 config.sub 均不支持 ohos 三元组，统一用
        --build/--host=aarch64-unknown-linux-gnu（仓库 libx11 配方同款，
        E007 显式三元组跳过平台检测）。
        rpath 通过环境变量 LDFLAGS 传入（clinfo 已验证的 make 机制）：
        `$$ORIGIN` 由 make 展开为 `$ORIGIN`，单引号防止 shell 吞掉。
        libX11/libXext 来自 conan 依赖（libx11/libxext 包），其 libdir 目录
        直接加进 LDFLAGS -L（不再依赖编译环境预编译栈，CI worker 栈可能
        完全没有 libX11）。
        """
        x11_inc, x11_lib = self._dep_dirs("libx11")
        stage = self._stage()
        vendor_inc = os.path.join(self.source_folder, "x11include")
        src = os.path.join(self.source_folder, "x11deps", name)
        # Conan 2 的 ConanFile.run() 不接受 dict 作 env 参数（只认环境脚本
        # 路径 str 或 list），传入 dict 会抛
        # "AssertionError: env argument to ConanFile.run() should be a list"。
        # 与 build() 里 os.environ["PWD"] 同源的 HMDFS 兜底思路一致：把变量
        # 直接并入 os.environ，再不带 env= 调用 run()。
        os.environ["PWD"] = src
        os.environ["CPPFLAGS"] = (f"-I{vendor_inc} -I{x11_inc} "
                                  + extra_cppflags).strip()
        os.environ["LDFLAGS"] = (f"-L{x11_lib} -L{stage}/lib "
                                 + extra_ldflags).strip()
        # configure 参数中 VAR=value 的值含空格时必须加单引号，否则
        # shell 会把 -I... 拆成独立参数
        def _q(arg):
            name_, _, value = arg.partition("=")
            if " " in value or "'" in value:
                return name_ + "=" + shlex.quote(value)
            return arg

        cfg = (f"./configure --prefix={stage} "
               f"--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu "
               f"--disable-docs --without-xmlto --without-fop "
               f"--without-xsltproc "
               + " ".join(_q(a) for a in configure_args))
        self.run(cfg, cwd=src)
        self.run("make -j1", cwd=src)
        if str(self.settings.os) == "OHOS":
            # E182/E188（adms 2.3.7 / libgsf 1.14.58 已过门禁同款）：HMBS
            # 的 install shim（runtime/<task>/bin/install）只接受单文件两参
            # 调用，libICE 1.1.1 旧式 automake 的 install-iceincludeHEADERS
            # 把 6 个头文件一次 `$(INSTALL_DATA) $$files dir` 批量拷贝
            # （install -c -m 644 f1..f6 dir/）→ 退出码 64 (EX_USAGE)。
            # 写 cp/mkdir shim 并重定向本库所有生成 Makefile 的 INSTALL，
            # INSTALL_DATA/INSTALL_PROGRAM 引用 ${INSTALL} 自动重算，
            # make install 全程走 shim。
            shim = self._write_install_shim()
            self._redirect_install_to_shim(src, shim)
        self.run("make install", cwd=src)

    def _write_install_shim(self):
        # E182/E188（adms 2.3.7 / libgsf 1.14.58 已过门禁同款）：HMBS 的
        # install shim 只接受单文件两参调用（多源 `install -c -m 644
        # f1..fN dir/` 直接 exit 64 = EX_USAGE）。这里写一个 cp/mkdir shim
        # 替代：解析 -c/-m/-d 等选项，末参为目标（目录或文件），逐源
        # cp 复制；HMFS 不支持 chmod（HMBS_CAP_CHMOD=0），chmod 步骤
        # 容错跳过。返回 shim 绝对路径供 Makefile INSTALL 重定向。
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        # HMFS 在创建时按 open mode 给权限（chmod 能力为 0），用 os.open
        # 指定 0o755 直接生成可执行 shim（同 adms 2.3.7 先例）。
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
                    "  # 多源形态：末参是目标目录，先确保目录存在\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  # HMFS 不支持 chmod（HMBS_CAP_CHMOD=0），设权限失败不阻断复制\n"
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
        except Exception:  # noqa: BLE001 - 写 shim 失败不静默，关闭 fd 后上抛
            os.close(fd)
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass  # HMFS 可能不支持 chmod（HMBS_CAP_CHMOD=0）
        return install

    def _redirect_install_to_shim(self, root, shim_install):
        # configure 已把探测到的 install 路径写死进各生成 Makefile 的
        # INSTALL 变量。把 `INSTALL = <.../install ...>` 替换为
        # `INSTALL = <shim>`，INSTALL_DATA/INSTALL_PROGRAM 默认
        # `${INSTALL} -m 644`/`${INSTALL}` 引用 ${INSTALL} 自动重算，
        # make install 全程走 shim（adms 2.3.7 同款）。
        for _root, _, _files in os.walk(root):
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

    def build(self):
        apply_conandata_patches(self)
        # CI worker PATH 缺工具链目录（flint/3.6.0 同款）：clang 绝对路径
        # 可用但内部 ld.lld/as/nm 走 PATH 失败 → "C compiler cannot create
        # executables"。先补 PATH 再跑任何 configure/make。
        self._prepend_toolchain_path()
        # HMDFS: conan 缓存父目录对 getcwd() 不可达，进程 cwd 固定到
        # build_folder 并预置 PWD，configure 顶部 pwd 判定回退 $PWD。
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder
        # 改写 source_folder 下所有 configure（含 x11deps 各库）的
        # pwd 判定与 config.status 临时目录 umask。
        self._rewrite_configure()

        # 内建缺失的 X11 依赖库（libXt 链接依赖 libSM/libICE，栈同样没有
        # 这两个库——ld.lld 报 unable to find library -lSM/-lICE 的直接根因）。
        # libX11/libXext 从 conan 依赖（libx11/6.4.0 + libxext/6.4.0）取，
        # 不再依赖预编译栈（CI worker 栈可能完全没有 libX11，CI #28097）。
        x11_inc, x11_lib = self._dep_dirs("libx11")
        xext_inc, xext_lib = self._dep_dirs("libxext")
        vendor_inc = os.path.join(self.source_folder, "x11include")
        stage = self._stage()
        xtrans_inc = os.path.join(self.source_folder, "x11deps", "xtrans")

        # libICE 1.1.1: 逃逸 ICE_CFLAGS/ICE_LIBS（xproto >= 7.0.25 xtrans）；
        # icetrans.c 直接 #include <X11/Xtrans/transport.c>（xtrans 源码头），
        # 编译/configure 均需 xtrans 头；libICE 不链接 X11（ICE_LIBS 置
        # 非空仅为满足 pkg.m4 逃逸条件）。
        self._build_vendored_lib("libICE", [
            "ICE_CFLAGS=-I{xtrans} -I{vendor} -I{x11}/include".format(
                xtrans=xtrans_inc, vendor=vendor_inc, x11=x11_inc),
            "ICE_LIBS=-L{x11}/lib".format(x11=x11_lib),
        ], extra_cppflags=f"-I{xtrans_inc}")
        # 立即物化 libICE 常规名：libSM 的 SM_LIBS 用 -lICE 走 stage/lib
        self._materialize_stage_libs(["libICE"])
        # libSM 1.2.4: 逃逸 SM_CFLAGS/SM_LIBS（ice >= 1.1.0 xproto xtrans）；
        # 链接 staging 的 libICE（-L{stage}/lib 前置）；sm_manager.c 引用
        # Xtrans.h；LIBUUID 探测缺包时 HAVE_LIBUUID=no 非致命（configure
        # 第 20565 行有 [HAVE_LIBUUID=no] 失败分支），无需逃逸。
        self._build_vendored_lib("libSM", [
            "SM_CFLAGS=-I{stage}/include -I{xtrans} -I{vendor} -I{x11}/include".format(
                stage=stage, xtrans=xtrans_inc, vendor=vendor_inc, x11=x11_inc),
            "SM_LIBS=-L{stage}/lib -L{x11}/lib -lICE".format(stage=stage, x11=x11_lib),
        ], extra_cppflags=f"-I{xtrans_inc}",
            extra_ldflags="-Wl,-rpath,'$$ORIGIN'")
        # 立即物化 libSM 常规名与 .so.6：libXt 的 XT_LIBS 用 -lSM/-lICE
        # 走 stage/lib，且 libXt.so.6 的 DT_NEEDED 会引用 libSM.so.6
        self._materialize_stage_libs(["libSM"])
        # libXt 1.2.1: 逃逸 XT_CFLAGS/XT_LIBS（sm ice x11 xproto kbproto），
        # -lSM/-lICE 指向 staging（真机栈没有这两个库，此前直接 -L{sys}/lib
        # 导致 ld.lld: unable to find library -lSM/-lICE）。
        self._build_vendored_lib("libXt", [
            "XT_CFLAGS=-I{stage}/include -I{vendor} -I{x11}/include".format(
                stage=stage, vendor=vendor_inc, x11=x11_inc),
            "XT_LIBS=-L{stage}/lib -L{x11}/lib -lSM -lICE -lX11".format(
                stage=stage, x11=x11_lib),
        ], extra_ldflags="-Wl,-rpath,'$$ORIGIN'")
        # 立即物化 libXt 常规名与 .so.6：libXmu 的 XMU_LIBS 用 -lXt 走
        # stage/lib
        self._materialize_stage_libs(["libXt"])
        # libXi 1.8.1: 逃逸 XI_CFLAGS/XI_LIBS（xproto/x11/xext/xextproto/
        # inputproto）；XFIXES 仅用于 PointerBarrier typedef 的 CFLAGS，
        # 逃逸 XFIXES_CFLAGS/XFIXES_LIBS 避免 xfixes.pc 依赖（值非空，
        # 否则 pkg.m4 会回落到 pkg-config）。
        self._build_vendored_lib("libXi", [
            "XI_CFLAGS=-I{vendor} -I{x11}/include -I{xext}/include".format(
                vendor=vendor_inc, x11=x11_inc, xext=xext_inc),
            "XI_LIBS=-L{x11}/lib -L{xext}/lib -lX11 -lXext".format(
                x11=x11_lib, xext=xext_lib),
            "XFIXES_CFLAGS=-I{vendor}".format(vendor=vendor_inc),
            "XFIXES_LIBS=-L{x11}/lib -L{xext}/lib".format(x11=x11_lib, xext=xext_lib),
        ])
        # libXmu 1.1.4: 逃逸 XMU_CFLAGS/XMU_LIBS（xt/xext/x11）与
        # XMUU_CFLAGS/XMUU_LIBS（x11）；-I 需含 staging 的 libXt 头；
        # 运行期依赖同目录的 libXt.so.6 → 额外加 $ORIGIN rpath。
        self._build_vendored_lib(
            "libXmu",
            [
                "XMU_CFLAGS=-I{stage}/include -I{vendor} -I{x11}/include -I{xext}/include".format(
                    stage=stage, vendor=vendor_inc, x11=x11_inc, xext=xext_inc),
                "XMU_LIBS=-L{stage}/lib -L{x11}/lib -L{xext}/lib -lXt -lXext -lX11".format(
                    stage=stage, x11=x11_lib, xext=xext_lib),
                "XMUU_CFLAGS=-I{vendor} -I{x11}/include".format(vendor=vendor_inc, x11=x11_inc),
                "XMUU_LIBS=-L{x11}/lib -lX11".format(x11=x11_lib),
            ],
            extra_ldflags="-Wl,-rpath,'$$ORIGIN'",
        )

        # 链接前物化 staging 里五个库的常规 .so 与 SONAME 名：xeyes 用
        # -lXi/-lXt/-lXmu 走 `-L{stage}/lib` 寻库，需要未版本化的
        # libXi.so/libXt.so/libXmu.so；libXt 的 DT_NEEDED 又是 libSM.so.6/
        # libICE.so.6（libSM 的 DT_NEEDED 是 libICE.so.6），链器按 SONAME
        # 名解析也需真实文件。libtool make install 产出的是 .so -> .so.6
        # 符号链接，HMFS 对 symlink 的物化不可靠（包阶段 E050 已为此专门
        # 规避）；把真实 SONAME 文件内容复制成常规名与 .so.6 名，保证链器
        # 必能在 stage/lib 找到。
        self._materialize_stage_libs()

        autotools = Autotools(self)
        autotools.configure()
        # 最终链接：make 命令行覆盖 LDFLAGS，加入 $ORIGIN rpath（打包后
        # 三个库与 xeyes 同在 bin/，运行时同目录寻库；clinfo 同款做法）。
        # shlex.quote 保证 '$$ORIGIN' 原样传给 make，由 make 展开为
        # $ORIGIN、单引号防 shell 吞掉。libX11/libXext 来自 conan 依赖
        # （libx11/libxext 包），链接时 -L 指向其 libdir；运行期依赖由
        # test_package 的 conanrun 环境（libdirs → LD_LIBRARY_PATH）与
        # LD_PRELOAD 兜底（见 test_package/conanfile.py）。
        link_ldflags = (f"-L{x11_lib} -L{xext_lib} "
                        f"-Wl,-rpath,'$$ORIGIN'")
        autotools.make(args=["-j1", "LDFLAGS=" + shlex.quote(link_ldflags)])

    def _materialize_stage_libs(self, libs=("libSM", "libICE", "libXi", "libXt", "libXmu")):
        """把 staging 里各库的真实 .so 复制成常规名与 .so.6 名。

        xeyes 链接命令行是 `-lXi -lXt -lXmu`，链器在 -L 路径里找 libXi.so /
        libXt.so / libXmu.so（常规非版本化名）；libXt 的 DT_NEEDED 又引用
        libSM.so.6/libICE.so.6（链器按 SONAME 名寻库）。vendored libtool
        make install 产出的是 .so -> .so.6 符号链接；HMFS 不保证 symlink
        物化（E050），一旦缺失链器直接报 `unable to find library -lXi`。
        把真实 SONAME 文件内容复制成常规名与 .so.6 名两个实体文件，任意
        寻库方式都能稳定命中（与 package() 里工具同款规避）。
        """
        stage_lib = os.path.join(self._stage(), "lib")
        for lib in libs:
            real = [p for p in _glob.glob(os.path.join(stage_lib, lib + ".so.*"))
                    if os.path.isfile(p) and not os.path.islink(p)]
            if not real:
                raise RuntimeError(f"vendored {lib} not installed to {stage_lib}")
            for plain in (lib + ".so", lib + ".so.6"):
                dst = os.path.join(stage_lib, plain)
                # 若目标已是真实文件（非 symlink）则跳过；否则把真实 SONAME
                # 文件内容直拷到常规名/.so.6 名（src/dst 同目录时 conan copy
                # 的同名复制不可靠，shutil.copy2 直接落地目标名最稳）
                if os.path.isfile(dst) and not os.path.islink(dst):
                    continue
                # 目标通常是 libtool make install 产出的符号链接链
                # （libICE.so -> libICE.so.6 -> libICE.so.6.3.0）：copy2 跟随
                # 链后与源 samefile → SameFileError（真机实测；HMFS 上
                # symlink 物化不可靠，E050）。先 unlink 旧项再复制成实体文件。
                try:
                    os.unlink(dst)
                except OSError:
                    pass
                shutil.copy2(real[0], dst)

    def _sign_elf(self, path):
        """ELF 代码签名（OHOS 内核拒绝未签名 ELF，clinfo 同款）。

        先剥掉可能存在的旧 .codesign 段再自签；chmod 失败容错（HMBS_CAP_CHMOD=0）。
        """
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # chmod may be unsupported on the device FS (HMBS_CAP_CHMOD=0)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 把内建的五个 X11 库（SONAME 命名）复制到 bin/ 与 xeyes 同目录，
        # rpath $ORIGIN 同目录寻库（clinfo 的 libOpenCL.so.1 同款做法）。
        # libXt.so.6 的 DT_NEEDED 是 libSM.so.6/libICE.so.6，必须一并随包。
        stage = self._stage()
        bin_dir = os.path.join(self.package_folder, "bin")
        for lib in ("libSM", "libICE", "libXt", "libXi", "libXmu"):
            real = [p for p in _glob.glob(os.path.join(stage, "lib", lib + ".so.*"))
                    if os.path.isfile(p) and not os.path.islink(p)]
            if not real:
                raise RuntimeError(f"vendored {lib} not found in {stage}/lib")
            src = real[0]
            copy(self, os.path.basename(src), os.path.dirname(src), bin_dir)
            dst = os.path.join(bin_dir, os.path.basename(src))
            # 以 SONAME 命名（libXt.so.6 / libXi.so.6 / libXmu.so.6 /
            # libSM.so.6 / libICE.so.6），避免依赖符号链接（HMDFS 不跟踪
            # symlink，E050）
            os.rename(dst, os.path.join(bin_dir, lib + ".so.6"))
        for f in os.listdir(bin_dir):
            self._sign_elf(os.path.join(bin_dir, f))

    def package_info(self):
        # 命令行工具：仅提供 bin/（R38）
        self.cpp_info.bindirs = ["bin"]
        # 五个 vendored X11 库（libXt/libXi/libXmu/libSM/libICE 的 .so.6）与
        # xeyes 同在 bin/：把 bin/ 声明为 libdirs，test_package 的 conanrun
        # 环境会把 <pkg>/bin 加入 LD_LIBRARY_PATH，运行时加载器不依赖 $ORIGIN
        # 也能找到随包库（test_package 真机执行 xeyes 时的双重保障）。
        self.cpp_info.libdirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
