#!/usr/bin/env python3
"""Conan recipe — xset/1.2.5 (X11 用户偏好设置命令行工具 bell/led/keymap/fp/dpms)

Build system: autotools。X.Org dist tarball 自带预生成 configure，故**不需要**
autoreconf，也就不需要 xorg-macros/util-macros 的 tool_requires（与仓库
libx11/6.4.0、libxext/6.4.0 同口径；xorg-macros 只在 autoreconf 阶段才用得上）。
License: MIT
Homepage: https://gitlab.freedesktop.org/xorg/app/xset

依赖判定（对 xset-1.2.5/configure.ac 实测，不是猜的）：
  - configure.ac:44  PKG_CHECK_MODULES(XSET, [xproto >= 7.0.17 xmuu])  2 参数＝硬失败
  - configure.ac:47  PKG_CHECK_MODULES(SET_X11, x11)                   硬失败
  - configure.ac:49  PKG_CHECK_MODULES(SET_XEXT, xext, [..], [echo not found])
  - configure.ac:55  PKG_CHECK_MODULES(SET_XKB, x11,  [..], [echo not found])
  - xf86misc 默认关（configure.ac USE_XF86MISC="no"）；fontcache 默认开，本配方
    显式 --without-fontcache（xfontcache 未发布；显式关闭保证 CI 与本地同形）
  ⇒ 精确依赖 = x11 + xext + xproto + **xmuu**。xmuu 不是可选项：
    xset.c:65 `#include <X11/Xmu/Error.h>`，xset.c:1681/1684 在 X 错误回调
    local_xerror 的通用分支调用 XmuPrintDefaultErrorMessage。

xmuu 的取法（本配方唯一的非常规步骤，证据链如下）：
  1. ohpcd 制品仓**没有** libxmu。全新 CONAN_HOME 下
     `conan download libxmu/1.3.1@ --remote=ohpcd --only-recipe` rc=1，
     stderr = "ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]"
     与故意构造的不存在包 bogus-no-pkg/9.9.9 的报错**逐字相同**，而同轮
     zlib/1.3.1 / libx11/6.4.0 / xorgproto/2025.1 均 rc=0（日志
     ~/tmp/uc2/z34-xset/logs/w0d-*.err）。
  2. archives/l/libxmu/1.3.1/ 确已合入 main，但「已合并 ≠ 制品可取」——仓库内
     现成佐证 archives/c/chiark-utils/8.0.1/conanfile.py:46 原文："needing
     libxmu/1.3.1, which is merged in main but NOT yet published to the
     registry (R36)"，其处置方式是把唯一消费者剔除出构建。
  3. ⇒ 按 E277 vendored 依赖模式（先例 archives/x/xeyes/1.3.1）从 X.Org 官方源
     构建 libXmuu。代价可控：libXmuu 只有 5 个源文件
     （libXmu-1.1.4/src/Makefile.am 的 libXmuu_la_SOURCES =
     ClientWin.c CursorName.c DefErrMsg.c GetHost.c Lower.c），且 libXmu 的
     configure.ac:33 `PKG_CHECK_MODULES(XMUU, x11)` 只依赖 x11 ⇒
     `make -C src libXmuu.la` 单独构建 mini 库，绕开全量 libXmu 的 xt 依赖
     （xt 同样未发布）。静态链入、不向系统目录装同名库（R26）。
"""
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XsetConan(ConanFile):
    name = "xset"
    version = "1.2.5"
    description = "User preference utility for X (bell/led/keymap/font path/DPMS)"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xset"
    url = "https://gitlab.freedesktop.org/xorg/app/xset"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xset supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # x11/xext/xproto 走 conan（ohpcd 已发布 OHOS armv8 binary；
        # xsel/1.2.1、libxext/6.4.0 同法）。xmuu 无已发布包，见模块 docstring。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def _source_kwargs(self, key):
        """conandata 里的 upstream_version 只是给人看的元数据，须剔除后
        再传给 get()（同 archives/l/libxext/6.4.0 的处理）。"""
        data = dict(self.conan_data["sources"][key])
        data.pop("upstream_version", None)
        return data

    def source(self):
        get(self, **self._source_kwargs("xset"), strip_root=True)
        # vendored libXmuu 源码（E277 模式），X.Org 官方 dist tarball，
        # 自带预生成 configure，故不需要 xorg-macros。
        get(self, **self._source_kwargs("libxmu"),
            destination="xmuu-src", strip_root=True)

    # ---------------------------------------------------------------- 路径

    def _stage(self):
        return os.path.join(self.build_folder, "xmuustage")

    def _libtool_shadow(self):
        """把各 host 依赖 libdir 里的库文件**不含 ``*.la``** 地汇集到一个私有
        shadow 目录，供 vendored libXmu 的 libtool 链接步使用。

        首轮实测（2026-09-25，archives/x/xset/1.2.5/reports/conan-create.log:340
        起）：libtool 沿 ``-lX11`` 在 conan 包目录里先命中 ``libX11.la``，读它的
        dependency_libs 去追 ``libxcb.la``（``libtool: warning: library
        '.../libxcb.la' was moved.``），再追 ``libXau.la``（``libtool: error:
        '.../libXau.la' is not a valid libtool archive``）——制品仓里的 .la 记的是
        打包机上的绝对路径，缓存一搬家就失效。仓库里同族问题的正规解法是
        archives/l/libxmu/1.3.1/conanfile.py 的 _prepare_ohos_libtool_shadow()
        （汇集 + 重写 .la 的 dependency_libs/libdir）。本包只需要一个**静态**
        libXmuu.a，libtool 记录下来的 dependency_libs 没有任何下游消费者 ⇒
        用"shadow 目录只放库文件、不放 .la"这个最小形态，让 ``-lX11`` 直接解析到
        普通 .so，不再进 .la 链。全程只读本包私有的 build_folder，不写、不改
        任何其它包的缓存目录。
        """
        shadow = os.path.join(self.build_folder, "libtool-shadow")
        os.makedirs(shadow, exist_ok=True)
        for libdir in self._dep_dirs("libdirs"):
            for entry in sorted(os.listdir(libdir)):
                if entry.endswith(".la") or entry.startswith("."):
                    continue
                src = os.path.join(libdir, entry)
                if not os.path.isfile(src):
                    continue
                dst = os.path.join(shadow, entry)
                if not os.path.exists(dst):
                    copy(self, entry, src=libdir, dst=shadow)
        return shadow

    def _dep_dirs(self, subdir):
        """所有 host 依赖的 include/lib 目录（去重、只保留真实存在的）。

        libxext/6.4.0 的 _dependency_dirs 同款做法，不硬编码机器路径。
        """
        result = []
        for dependency in self.dependencies.host.values():
            for entry in getattr(dependency.cpp_info, subdir, None) or []:
                path = os.path.join(dependency.package_folder, entry)
                if os.path.isdir(path) and path not in result:
                    result.append(path)
        return result

    def _gnu_triplet(self):
        arch = str(self.settings.arch)
        machine = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "x86_64": "x86_64",
            "armv7": "arm",
        }.get(arch, arch)
        return f"{machine}-unknown-linux-gnu"

    # ------------------------------------------------------------- generate

    def _write_xmuu_pc(self):
        """为 vendored libXmuu 写 xmuu.pc，让 configure.ac:44 的
        PKG_CHECK_MODULES(XSET, [xproto >= 7.0.17 xmuu]) 走**真实 pkg-config 探测**
        ——而不是预置 XSET_CFLAGS/XSET_LIBS 把整条探测短路掉。
        Requires 里带上 xproto/x11，pkg-config 会自动把 -lX11 与 X11 头目录
        一并算进 XSET_LIBS/XSET_CFLAGS。"""
        upstream_version = str(
            self.conan_data["sources"]["libxmu"].get("upstream_version", ""))
        content = (
            "prefix=%s\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: Xmuu\n"
            "Description: Mini Xmu Library (vendored from libXmu %s by this recipe)\n"
            "Version: %s\n"
            "Requires: xproto x11\n"
            "Cflags: -I${includedir}\n"
            "Libs: -L${libdir} -lXmuu\n"
        ) % (self._stage(), upstream_version, upstream_version)
        path = os.path.join(self.generators_folder, "xmuu.pc")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def generate(self):
        # PkgConfigDeps 生成 x11.pc / xext.pc / xproto.pc（含传递依赖），供
        # xset 的 SET_X11 / SET_XEXT / SET_XKB 与 xmuu.pc 的 Requires 使用。
        PkgConfigDeps(self).generate()
        self._write_xmuu_pc()

        tc = AutotoolsToolchain(self)
        # config.guess 认不出 HarmonyOS（uname -s 输出 "HarmonyOS"）→ 显式三元组
        # 绕过（同仓库 libxext/6.4.0、xsel/1.2.1、a52dec/0.7.4）。
        if str(self.settings.os) == "OHOS":
            gnu_triplet = self._gnu_triplet()
            tc.configure_args.append(f"--build={gnu_triplet}")
            tc.configure_args.append(f"--host={gnu_triplet}")
        # xfontcache 未发布。fontcache 探测是 4 参数条件式（缺了只 echo not
        # found），但默认值是 yes ⇒ 显式关闭，避免 CI/本地走到不同分支。
        tc.configure_args.append("--without-fontcache")
        tc.generate()

    # ---------------------------------------------------------------- build

    def _restore_script_modes(self, root):
        """E490（G0 预扫点名）：autotools 的辅助脚本是**可执行程序**，但解包路径
        可能保住内容却丢掉执行位 → configure/make 阶段报 Permission denied。
        这里对仓库已知的辅助脚本集合幂等补 +x（两棵源码树都要：xset 本体与
        vendored libXmu）。HMFS 上 chmod 可能是 no-op（E046），故全程容错。"""
        for name in ("configure", "config.guess", "config.sub", "install-sh",
                     "missing", "mkinstalldirs", "compile", "depcomp",
                     "ar-lib", "test-driver", "ltmain.sh"):
            path = os.path.join(root, name)
            if not os.path.isfile(path):
                continue
            try:
                mode = os.stat(path).st_mode
                os.chmod(path, mode | 0o111)
            except OSError:
                self.output.warn(f"E490: chmod +x 失败（HMFS 可能忽略权限位）：{path}")

    def build(self):
        # HMDFS/HMFS 不支持 getcwd：进程 cwd 切到 build_folder 并预置 PWD，
        # 让子进程 shell 的 pwd 内建走逻辑路径（同 xsel/1.2.1、aribb24/1.0.4）。
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder
        os.umask(0)

        self._restore_script_modes(self.source_folder)
        apply_conandata_patches(self)
        self._patch_configure(os.path.join(self.source_folder, "configure"))

        self._build_xmuu()

        # xsel/1.2.1 实测：真机 conan 2.x 由 PkgConfigDeps/AutotoolsToolchain
        # 注入的 PKG_CONFIG_PATH 不生效，须在 build() 作用域内注入并在结束时恢复
        # （try/finally）。xmuu.pc 在 generators 根目录，一并进搜索路径。
        pc_paths = [self.generators_folder]
        pc_paths += [os.path.join(path, "pkgconfig")
                     for path in self._dep_dirs("libdirs")]
        prior = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = ":".join(pc_paths)
        self.output.info(
            f"PKG_CONFIG_PATH (scoped) = {os.environ['PKG_CONFIG_PATH']}")
        try:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
        finally:
            if prior:
                os.environ["PKG_CONFIG_PATH"] = prior
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)

    def _build_xmuu(self):
        """构建 vendored libXmuu（只构建 mini 库，不构建需要 xt 的全量 libXmu）。

        libXmu 的 configure 用 PKG_CHECK_MODULES(XMU, xt xext x11 xextproto) 探测
        全量 libXmu 的依赖，而 xt 同样未发布 ⇒ 用 pkg.m4 文档化的
        XMU_CFLAGS/XMU_LIBS 覆盖口（以 configure 命令行 VAR=value 传入，含空格处
        shlex.quote）把这条探测短路掉；随后只 make 目标 libXmuu.la。
        """
        stage = self._stage()
        src = os.path.join(self.source_folder, "xmuu-src")
        self._restore_script_modes(src)
        self._patch_configure(os.path.join(src, "configure"))

        cflags = " ".join(f"-I{path}" for path in self._dep_dirs("includedirs"))
        # 全部 -l 只走 shadow 目录（理由见 _libtool_shadow 的 docstring）。
        # XMU_* 覆盖的是 configure.ac:32 那条 `PKG_CHECK_MODULES(XMU, xt xext x11
        # xextproto)`——xt 无已发布制品，必须短路；XMUU_* 覆盖 configure.ac:33 的
        # `PKG_CHECK_MODULES(XMUU, x11)`，它的值才是 libXmuu_la_LIBADD 真正进
        # libtool 链接步的东西。两者都非空才会被 pkg.m4 当作覆盖值采用。
        shadow = self._libtool_shadow()
        libs = f"-L{shadow} -lX11"
        gnu_triplet = self._gnu_triplet()
        configure_cmd = " ".join([
            "./configure",
            f"--prefix={stage}",
            "--sysconfdir=/etc",
            "--localstatedir=/var",
            f"--build={gnu_triplet}",
            f"--host={gnu_triplet}",
            # 静态入库：只出 .a 交叉链进 xset，不装同名 .so（R26）
            "--disable-shared",
            "--enable-static",
            "--with-pic",
            # libXmu 带 doc/ + docbook.am，CI 无 xmlto/fop，显式关闭文档链
            "--disable-docs",
            "--without-xmlto",
            "--without-fop",
            "--without-xsltproc",
            f"XMU_CFLAGS={shlex.quote(cflags)}",
            f"XMU_LIBS={shlex.quote(libs)}",
            f"XMUU_CFLAGS={shlex.quote(cflags)}",
            f"XMUU_LIBS={shlex.quote(libs)}",
        ])
        prior_pwd = os.environ.get("PWD", "")
        os.environ["PWD"] = src
        self.run(configure_cmd, cwd=src, env="conanbuild")
        self.run("make -C src libXmuu.la -j1", cwd=src, env="conanbuild")
        os.environ["PWD"] = prior_pwd

        # 手工装配 staging（不跑 make install：顶层 install 会去构建未满足的
        # libXmu；且 HMBS 的 install shim 对多源调用直接 exit 64 = E182）
        built = None
        for candidate in (os.path.join(src, "src", ".libs", "libXmuu.a"),
                          os.path.join(src, "src", "libXmuu.a")):
            if os.path.isfile(candidate):
                built = candidate
                break
        if built is None:
            raise RuntimeError(
                "libXmuu.a 未生成：make -C src libXmuu.la 之后 src/.libs 与 src/ "
                "均无 libXmuu.a ⇒ vendored 构建失败。请查本轮 build 日志的第一条"
                "真实错误，不得据此改判为「依赖未发布」。"
            )
        os.makedirs(os.path.join(stage, "lib"), exist_ok=True)
        copy(self, os.path.basename(built), src=os.path.dirname(built),
             dst=os.path.join(stage, "lib"))
        copy(self, "X11/Xmu/*.h", src=os.path.join(src, "include"),
             dst=os.path.join(stage, "include"))
        self.output.info(
            f"vendored libXmuu -> {os.path.join(stage, 'lib', os.path.basename(built))}")

    def _patch_configure(self, cfg):
        """改写生成的 configure（同 xsel/1.2.1）：
        - E114：config.status 用 umask 077 建临时目录，HMDFS 下不可写 → 022；
        - HMDFS 下 getcwd 不可达 → configure 报 'working directory cannot be
          determined'：autoconf 2.70+ 的 `ac_pwd=`pwd`` 追加 $PWD 兜底，
          2.69 的 `if (pwd) >/dev/null 2>&1` 追加 `|| test -n "$PWD"`。"""
        if not os.path.isfile(cfg):
            return
        with open(cfg, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        original = text
        text = text.replace("umask 077", "umask 022")
        if "ac_pwd=`pwd`" in text and 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"' not in text:
            text = text.replace("ac_pwd=`pwd`",
                                'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
        text = re.sub(
            r"if \(pwd\) >/dev/null 2>&1( && test -d \"`pwd`\")?; then :; else",
            r"if (pwd) >/dev/null 2>&1\1 || test -n \"$PWD\"; then :; else",
            text,
        )
        if text != original:
            with open(cfg, "w", encoding="utf-8") as handle:
                handle.write(text)

    # -------------------------------------------------------------- package

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # 应用包不留 libtool 描述文件
        for root, _dirs, files in os.walk(
                os.path.join(self.package_folder, "lib")):
            for name in list(files):
                if name.endswith(".la"):
                    os.remove(os.path.join(root, name))

    def package_info(self):
        # 命令行工具：bin/xset，无可链接库（libXmuu 已静态链入）
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
