#!/usr/bin/env python3
"""Conan recipe — xprop 1.2.8 (X11 窗口属性探测器)

Build system: autotools（上游 tarball 自带已生成的 configure，免 autoreconf；
XORG_MACROS_VERSION/XORG_DEFAULT_OPTIONS 仅 autoreconf 时展开，此处不触发）
License: MIT-custom (X11)、MIT、HPND — 见 COPYING
Homepage: https://gitlab.freedesktop.org/xorg/app/xprop

依赖说明（xeyes 1.3.1 同款先例，CI #28097）：X11 链接库/头文件来自 conan
依赖 libx11/6.4.0（Track B；xprop 只链 -lX11，不含任何钉轨 X11 子库——
依赖集合未命中 DRAFT-xbanish-1.8-x11-track-selection 的钉轨者表，属"未命中
任何钉轨者"的平凡路径）+ xorgproto/2025.1（X11/Xproto.h、keysymdef.h 等
xproto 头，configure.ac L42 要求 xproto >= 7.0.25）。不再依赖编译环境
预编译栈（CI worker 栈可能完全没有 libX11）。
运行期：libX11.so.6 的 DT_NEEDED 需要 libxcb.so.1/libXau.so.6（libxcb 又链
libXau/libXdmcp），主配方以 libxcb/1.16 + libxau/1.0.11（run=True）补齐，
test_package 用 LD_PRELOAD 绝对路径注入（HMBS [stale_runtime_library]）。

configure 逃逸：configure.ac L42 PKG_CHECK_MODULES(XPROP, [x11 xproto >= 7.0.25])
——预置 XPROP_CFLAGS/XPROP_LIBS 后 configure 直接采用、不再调用 pkg-config
（adcli KRB5_CFLAGS/KRB5_LIBS、coturn SSL_CFLAGS/SSL_LIBS、xeyes XEYES_*
同款先例；conan 包不随附 xproto.pc/x11.pc 全集，逃逸避免 pkg-config 依赖）。

上游无测试套件：Makefile.am 仅 bin_PROGRAMS + man，无 TESTS/check 目标，
源码树无 tests/ 目录（四类口径审计见 test_package/MANIFEST.yml）。
test_package 真实执行被测二进制（★实测口径）：xprop 非 Xt 程序，main 在
解析任何参数（含 -version/-root）前先经 dsimple.c Open_Display 连接
X server——dsimple.c L106 XOpenDisplay 失败后 fprintf "unable to open
display" 并 exit(1)；本平台无 X server，两项断言（-version 与 -root）
均走上游确定性 no-X 错误路径（rc=1），不冒充功能级真机验证
（not_covered 见 test_package/MANIFEST.yml）。

HMDFS 适配（xeyes 同款）：conan 缓存父目录对 getcwd() 不可达 → build() 固定
cwd 到 build_folder 并预置 PWD；_rewrite_configure 改写 configure 顶部 pwd
判定回退 $PWD、config.status 临时目录 umask 077 → 022（E114/E129）。
"""
import glob as _glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XpropConan(ConanFile):
    name = "xprop"
    version = "1.2.8"
    description = "Property displayer for X"
    license = ("MIT-custom", "MIT", "HPND")
    homepage = "https://gitlab.freedesktop.org/xorg/app/xprop"
    url = homepage
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # xeyes 1.3.1 / xclip / xsel 同款：conan 依赖取 X11，不依赖 worker
        # 预编译栈。libxcb/libxau 是 libX11.so.6 运行期 DT_NEEDED（run=True
        # 使 test_package 的 conanrun 环境注入其 libdir）。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("libxcb/1.16", run=True)
        self.requires("libxau/1.0.11", run=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # 本包当前无补丁，conandata.yml 无 patches 块时为 no-op；
        # 保留标准补丁导出通道（G1 配方完整性 / R25，xeyes 同款）
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["xprop"], strip_root=True)

    def _dep_dirs(self, name, header_only=False):
        """依赖包的 include/lib 目录（xeyes 同款）。

        header_only：纯头文件包（如 xorgproto）cpp_info.libdirs 为空，
        取 libdirs[0] 会 IndexError，置 header_only=True 只取 include。
        """
        dep = self.dependencies[name]
        inc = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
        if header_only:
            return inc, None
        lib = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        return inc, lib

    def _rewrite_configure(self):
        """HMDFS getcwd 兜底：改写 configure 的 pwd 判定与 umask（xeyes 同款）。

        conan 缓存父目录对 getcwd() 不可达（路径查找可用、getcwd() 沿父链
        上溯失败），configure 顶部 `pwd` 判定报 "working directory cannot be
        determined"。改写为 pwd 失败时回退 $PWD（nspr/aribb24/libgsf 同款）；
        config.status 临时目录 umask 077 → 022（E114/E129）。
        """
        for _cfg in _glob.glob(os.path.join(self.source_folder, "configure")):
            try:
                with open(_cfg, "r", encoding="utf-8", errors="ignore") as _f:
                    _text = _f.read()
            except OSError:
                continue
            _text = _text.replace("umask 077", "umask 022")
            if 'ac_pwd=`pwd` && test -n "$ac_pwd" &&' in _text:
                _text = _text.replace(
                    'ac_pwd=`pwd` && test -n "$ac_pwd" &&',
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"\ntest -n "$ac_pwd" &&',
                    1,
                )
            elif "if (pwd) >/dev/null 2>&1; then :; else" in _text:
                _text = _text.replace(
                    "if (pwd) >/dev/null 2>&1; then :; else",
                    'if (pwd) >/dev/null 2>&1 || test -n "$PWD"; then :; else',
                )
            with open(_cfg, "w", encoding="utf-8") as _f:
                _f.write(_text)

    def generate(self):
        tc = AutotoolsToolchain(self)
        x11_inc, x11_lib = self._dep_dirs("libx11")
        proto_inc, _ = self._dep_dirs("xorgproto", header_only=True)
        tc.configure_args.append(f"--x-includes={x11_inc}")
        tc.configure_args.append(f"--x-libraries={x11_lib}")
        # 交叉编译模式（E007 显式三元组跳过平台检测）：xprop 1.2.8 的
        # config.sub（2024 版）不认 ohos OS（实测 Invalid configuration
        # 'aarch64-unknown-linux-ohos'），与 xeyes vendored 库/仓库 libx11
        # 配方同款统一用 gnu 三元组；交叉工具链由 toolchain 的 CC/CXX 保证。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # PKG_CHECK_MODULES(XPROP, [x11 xproto >= 7.0.25]) 逃逸：预置
        # XPROP_CFLAGS/XPROP_LIBS 后 configure 直接采用、不再调 pkg-config。
        # xprop 只链接 -lX11（Makefile.am xprop_LDADD = $(XPROP_LIBS)）。
        tc.configure_args.append(
            "XPROP_CFLAGS=-I{} -I{}".format(x11_inc, proto_inc))
        tc.configure_args.append("XPROP_LIBS=-L{} -lX11".format(x11_lib))
        tc.generate()

    def build(self):
        # HMDFS：conan 缓存父目录对 getcwd() 不可达 → cwd 固定 build_folder
        # 并预置 PWD（configure 顶部 pwd 判定回退 $PWD；xeyes 同款）。
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder
        self._rewrite_configure()
        # 本包无补丁：apply 为 no-op，保留标准补丁应用位置（G1 / R25）
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def _sign_elf(self, path):
        """ELF 代码签名（OHOS 内核拒绝未签名 ELF，xeyes/clinfo 同款）。

        先剥掉可能存在的旧 .codesign 段再自签；chmod 失败容错
        （HMBS_CAP_CHMOD=0）。
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
        # 只保留可执行体目录内的产物并签名（man 页随 share/ 保留不影响 R38）
        self._sign_elf(os.path.join(self.package_folder, "bin", "xprop"))

    def package_info(self):
        # 命令行工具：仅提供 bin/（R38）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
