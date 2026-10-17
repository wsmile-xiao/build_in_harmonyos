#!/usr/bin/env python3
"""Conan recipe — xev 1.2.7 (X11 event dumper)

Build system: autotools (上游 tarball 自带 autoconf 2.73 生成的 configure，
无需 autoreconf；显式 --host 三元组绕开 config.guess，config.sub 已支持
ohos*/linux-ohos*)。评估过 meson 路线（tarball 同时带 meson.build），但 meson
需在 OHOS worker 上证明 meson+ninja 工具链可用，且全部 X 应用先例
（xeyes/xterm/xclip）走 autotools，故按最小风险取 autotools。

License: MIT (X11)
Homepage: https://gitlab.freedesktop.org/xorg/app/xev

依赖：xev 仅链接 Xlib + XRandR（configure.ac:
PKG_CHECK_MODULES(XEV, [xrandr >= 1.2 x11 xproto >= 7.0.22])；
Makefile.am: xev_LDADD = $(XEV_LIBS), AM_CFLAGS = $(XEV_CFLAGS)）。库全部
取 ohpcd 已发布 OHOS armv8 二进制（W0 --only-recipe 已核）：
  - libx11/6.4.0
  - libxrandr/1.5.5.1（钉 libxext/6.4.0 + libxrender/0.9.12 + xorgproto/2025.1）
运行期 DT_NEEDED 兜底：libX11.so.6 → libxcb.so.1 + libXau.so.6（libxcb →
libXau/libXdmcp），显式声明 run 依赖（libxcb/1.16 + libxau/1.0.11），与 xeyes
同款，供 test_package 的 conanrun 环境注入 libdir + LD_PRELOAD 兜底。

不依赖编译环境预编译 X11 栈（/storage/Users/currentUser/usr/local）：CI
worker 的栈可能完全没有 libX11（xeyes CI #28097 实证），全部走 conan 依赖。

上游无自动化测试：Makefile.am 无 check/TESTS、meson.build 无 test()、源码树
无 tests/、xev.c 无 assert()（审计见 test_package/MANIFEST.yml）。test_package
以 `xev -version/--version/-help` + 非法选项退出码真实执行被测二进制——这些
路径在 xev.c 中均早于 XOpenDisplay（第 1384 行）返回，无需 X server。
"""
import glob as _glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class XevConan(ConanFile):
    name = "xev"
    version = "1.2.7"
    description = ("X11 event dumper: prints keyboard, mouse, focus and "
                   "XRandR events received by a window")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xev"
    url = "https://gitlab.freedesktop.org/xorg/app/xev"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 链接库全部来自 conan 依赖（ohpcd 已发布 OHOS armv8 binary）。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxrandr/1.5.5.1", transitive_headers=True, transitive_libs=True)
        # 运行期 DT_NEEDED 兜底：libX11.so.6 需要 libxcb.so.1 + libXau.so.6，
        # libxcb 需要 libXau/libXdmcp。显式 run 依赖让 test_package 的
        # conanrun 环境注入其 libdir（LD_LIBRARY_PATH），配合 LD_PRELOAD。
        self.requires("libxcb/1.16", run=True)
        self.requires("libxau/1.0.11", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _pkg_config_dirs(self):
        """收集所有 host 依赖的 pkgconfig 目录（lib/pkgconfig + share/pkgconfig）。

        xorgproto 的协议 .pc（xproto/randrproto/kbproto 等）装在 share/pkgconfig，
        libx11/libxrandr/libxext/libxrender 的 .pc 装在 lib/pkgconfig。configure 的
        PKG_CHECK_MODULES(XEV,[xrandr x11 xproto]) 需要 PKG_CONFIG_PATH 覆盖二者。
        """
        out = []
        for dep in self.dependencies.host.values():
            for sub in (os.path.join("lib", "pkgconfig"),
                        os.path.join("share", "pkgconfig")):
                d = os.path.join(dep.package_folder, sub)
                if os.path.isdir(d) and d not in out:
                    out.append(d)
        return out

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 交叉三元组：--host 显式给出，绕开 config.guess 探测；config.sub
        # (xev 1.2.7 自带) 已支持 linux-ohos*（xeyes 同款）。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # 依赖的 include/lib 与 -l 交由 AutotoolsDeps 注入构建环境（xev.c 需要
        # <X11/Xlocale.h> 等 libX11 头，靠 conan 依赖的 cpp_info 传播）。
        # PKG_CHECK_MODULES(XEV,[xrandr x11 xproto]) 走真实 pkg-config：把全部
        # 依赖的 lib/pkgconfig 与 share/pkgconfig 加进 PKG_CONFIG_PATH（xorgproto
        # 协议 .pc 在 share/pkgconfig），让 configure 解析出正确的 XEV_CFLAGS/
        # XEV_LIBS。
        pkg_path = ":".join(self._pkg_config_dirs())
        cur = os.environ.get("PKG_CONFIG_PATH", "").strip()
        if cur:
            pkg_path = pkg_path + ":" + cur
        # 把 PKG_CONFIG_PATH 作为 configure 命令行变量注入（xeyes 同款），
        # 让 PKG_CHECK_MODULES(XEV,[xrandr x11 xproto]) 的 pkg-config 解析成功。
        tc.configure_args.append(f"PKG_CONFIG_PATH={pkg_path}")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def _prepend_toolchain_path(self):
        """CI worker PATH 缺工具链目录（xeyes/flint 同款）：clang 绝对路径可用
        但其内部 ld.lld/as/nm 走 PATH 解析 → configure 报 "C compiler cannot
        create executables"。从 compiler_executables 推导工具目录并前置 PATH。
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
        """HMDFS getcwd 兜底（xeyes/nspr/libgsf 同款）：conan 缓存父目录对
        getcwd() 不可达，configure 顶部 `pwd` 判定报 "working directory cannot
        be determined"。pwd 失败回退 $PWD；config.status 临时目录 umask 077→022。
        """
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
                    1,
                )
            elif "if (pwd) >/dev/null 2>&1; then :; else" in _text:
                _text = _text.replace(
                    "if (pwd) >/dev/null 2>&1; then :; else",
                    "if (pwd) >/dev/null 2>&1 || test -n \"$PWD\"; then :; else",
                )
            if _text != _orig:
                with open(_cfg, "w", encoding="utf-8") as _f:
                    _f.write(_text)

    def build(self):
        apply_conandata_patches(self)
        self._prepend_toolchain_path()
        # HMDFS：进程 cwd 固定到 build_folder 并预置 PWD，configure 的 pwd
        # 判定回退 $PWD。
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder
        self._rewrite_configure()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _sign_elf(self, path):
        """ELF 代码签名（OHOS 内核拒绝未签名 ELF，xeyes/clinfo 同款）。"""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # HMFS 可能不支持 chmod（HMBS_CAP_CHMOD=0）

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for f in sorted(os.listdir(bin_dir)):
                self._sign_elf(os.path.join(bin_dir, f))

    def package_info(self):
        # 命令行工具：仅暴露 bin/（R38）；不导出库/头。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
