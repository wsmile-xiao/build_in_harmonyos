#!/usr/bin/env python3
"""Conan recipe — xgamma 1.0.8 (X11 gamma/brightness tuner, XFree86-VidModeExtension)

Build system: autotools（上游 tarball 自带 autoconf 预生成 configure，无需
autoreconf；显式 --host 三元组绕开 config.guess——tarball 内 config.guess 出
现 0 次 ohos，而 config.sub 第 2070/2213 行已支持 ohos*/linux-ohos*，同 xev）。
评估过 meson 路线（tarball 同时带 meson.build），但 meson 需在 OHOS worker 上
证明 meson+ninja 可用，且全部 X 应用先例（xev/xeyes/xterm/xclip）走 autotools，
按最小风险取 autotools。

License: MIT (X11)
Homepage: https://gitlab.freedesktop.org/xorg/app/xgamma

依赖：xgamma 仅链接 Xlib + XFree86-VidModeExtension（configure.ac:
`PKG_CHECK_MODULES(XGAMMA, [x11 xxf86vm xproto >= 7.0.17])`；Makefile.am:
`xgamma_LDADD = $(XGAMMA_LIBS)`、`AM_CFLAGS = $(CWARNFLAGS) $(XGAMMA_CFLAGS)`、
`xgamma_SOURCES = xgamma.c`）。库全部取 ohpcd 已发布 OHOS armv8 二进制
（W0 实证：preflight RC=0 + 精确 `conan install --build=never` 真下载到包，
未使用通配 conan list——R35）：
  - libx11/6.4.0
  - libxxf86vm/1.1.5（其钉 libx11/6.4.0 + libxext/6.4.0 + xorgproto/2025.1，
    与本配方同源，不产生版本冲突）
  - xorgproto/2025.1（提供 xproto.pc，configure 的 xproto >= 7.0.17 判定需要它；
    libxxf86vm 已传递引入，此处显式声明以固化 PKG_CONFIG_PATH 解析）
运行期 DT_NEEDED 兜底：libXxf86vm.so.1 → libX11.so.6 → libxcb.so.1 +
libXau.so.6（libxcb → libXau/libXdmcp），显式声明 run 依赖（libxcb/1.16 +
libxau/1.0.11），与 xev 同款，供 test_package 的 conanrun 环境注入 libdir +
LD_PRELOAD 兜底。

不依赖编译环境预编译 X11 栈（/storage/Users/currentUser/usr/local）：CI worker
的栈可能完全没有 libX11（xeyes CI #28097 实证），全部走 conan 依赖。

上游无自动化测试：Makefile.am 无 TESTS/check_PROGRAMS（Makefile.in 仅有 automake
样板 `check: check-recursive`）、meson.build 无 test()、源码树无 tests/、
xgamma.c 无 assert()（行首锚定 grep 计数 = 0）。test_package 真实
执行被测二进制的 9 条命令行路径做无头断言（详见 test_package/MANIFEST.yml）：
版本号、usage、非法参数、**gamma 取值域校验（GAMMA_MIN/GAMMA_MAX）**、
-gamma 与 -rgamma/-ggamma/-bgamma 互斥、缺参数、只读查询——这些路径在 xgamma.c
中均早于第 202 行 `XOpenDisplay` 返回，无需 X server，且**不可能触碰
XF86VidModeSetGamma**（安全红线：绝不在真机留下被改掉的 gamma 状态）。
"""
import glob as _glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class XgammaConan(ConanFile):
    name = "xgamma"
    version = "1.0.8"
    description = ("X11 command line gamma/brightness tuner: query and set the "
                   "gamma of an X screen via XFree86-VidModeExtension")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xgamma"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 链接库全部来自 conan 依赖（ohpcd 已发布 OHOS armv8 binary）。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxxf86vm/1.1.5", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
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

        xorgproto 的协议 .pc（xproto.pc 等）装在 share/pkgconfig，
        libx11/libxxf86vm/libxext 的 .pc 装在 lib/pkgconfig。configure 的
        PKG_CHECK_MODULES(XGAMMA,[x11 xxf86vm xproto >= 7.0.17]) 需要
        PKG_CONFIG_PATH 同时覆盖二者。
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
        # 交叉三元组：--host 显式给出，绕开 config.guess 探测（tarball 内
        # config.guess 不认 ohos）；config.sub 已支持 linux-ohos*（xev 同款）。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # 依赖的 include/lib 与 -l 交由 AutotoolsDeps 注入构建环境。
        # PKG_CHECK_MODULES(XGAMMA,[x11 xxf86vm xproto]) 走真实 pkg-config：把全部
        # 依赖的 lib/pkgconfig 与 share/pkgconfig 加进 PKG_CONFIG_PATH，让
        # configure 解析出正确的 XGAMMA_CFLAGS / XGAMMA_LIBS（含 -lXxf86vm -lX11）。
        pkg_path = ":".join(self._pkg_config_dirs())
        cur = os.environ.get("PKG_CONFIG_PATH", "").strip()
        if cur:
            pkg_path = pkg_path + ":" + cur
        # 作为 configure 命令行变量注入（xev/xeyes 同款；AutotoolsToolchain 无
        # extra_env 属性，见 xev notes 失败方案 B）。
        tc.configure_args.append(f"PKG_CONFIG_PATH={pkg_path}")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def _prepend_toolchain_path(self):
        """E540：CI worker PATH 缺工具链目录（xeyes/flint/xev 同款）——clang 绝对
        路径可用但其内部 ld.lld/as/nm 走 PATH 解析，profile 的 CC/CXX 指向
        /data/service/hnp/bin/clang 而该目录不在 runner PATH 时，首个 make 直接
        exit 127。从 tools.build:compiler_executables 推导工具目录并前置 PATH
        （幂等，不硬编码机器路径）。
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
        """HMDFS getcwd 兜底（xeyes/nspr/libgsf/xev 同款）：conan 缓存父目录对
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
        """ELF 代码签名（OHOS 内核拒绝未签名 ELF，xeyes/clinfo/xev 同款）。"""
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
