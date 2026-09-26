#!/usr/bin/env python3
"""Conan recipe — xrefresh 1.1.0（让 X server 重绘全部窗口的命令行工具）

Build system: autotools（上游预生成 configure），单文件 C（xrefresh.c）
License: MIT
Homepage: https://gitlab.freedesktop.org/xorg/app/xrefresh

依赖口径 = 实证，不是台账声明。configure.ac 里只有一条
`PKG_CHECK_MODULES(XREFRESH, [x11 xproto >= 7.0.25])`，xrefresh.c 只
include <X11/Xos.h>/<X11/Xlib.h>/<X11/Xutil.h>，产物 DT_NEEDED 实测只有
`libX11.so.6` + `libc.so`（llvm-readelf -d，见 notes.md 验证结果）。
⇒ 本配方**不内建（vendored）任何第三方源码**：需要 libXmu/xmuu 而被迫停手的是
同族 xhost，xrefresh 的模块清单里没有 xmu/xmuu/xt。

依赖选择（W0 二进制层实测，均 `conan install --build=never
-pr:h/-pr:b=ci/conan/profiles/ohos-aarch64` 到 "Install finished successfully"）：
- libx11/6.4.0            构建 + 链接（104 个在档配方用的就是这条版本线）
- xorgproto/2025.1        xproto.pc 与 X11/Xos.h、X11/Xfuncproto.h、X11/X.h
                          （xorgproto/2024.1 未发布，与必然不存在的负对照同签名）
- libxcb/1.16 + libxau/1.0.11 + libxdmcp/1.1.5  只作运行期闭包：
  libX11.so.6 → libxcb.so.1 → libXau.so.6 + libXdmcp.so.6。真机实测过缺
  libXdmcp 时 musl loader 直接 `Error relocating ... XdmcpWrap: symbol not
  found`，所以三个都显式声明（run=True），让 test_package 的 conanrun 环境
  拿到它们的 libdir。已发布二进制里 libxcb.so.1 的 RUNPATH 是构建机
  .conan2 绝对路径（换 CONAN_HOME 即失效），故 test_package 再以 LD_PRELOAD
  绝对路径兜底（同族 xeyes 1.3.1 同款处置）。

平台适配三处，全部走 patches/（由 finish 的 refresh-patch --auto 生成）：
1) config.guess 增加 `*:HarmonyOS:*:*` 分支 → aarch64-unknown-linux-ohos
   （E007/E160；同时让 config.guess 在撞 HMDFS 之前短路——未打补丁时基线首错是
   `./config.guess[1572]: can't create .../dummy.c: Permission denied`，
   随后 `configure: error: cannot guess build type; you must specify one`）
2) config.sub 三处：ohos-linux 映射、OS 白名单加 ohos*、kernel-OS 白名单加
   linux-ohos*（E007/E072/E122；缺第三处时 config.guess 已能猜出三元组，
   config.sub 仍报 `Kernel 'linux' not known to work with OS 'ohos'`）
3) configure 的 config.status 临时目录引导去掉 `umask 077`（E136）
   对照实验（同目录、同 TMPDIR）：umask077+相对=drwx--S--- 不可写；
   umask022/不给 umask=drwxr-s--x 可写；**umask077+绝对 $TMPDIR 仍不可写**
   ⇒ E136 里"改走 TMPDIR"那半是无效动作，唯一因果是 umask 077。

按 R1/E205：不用 --build/--host 三元组绕过平台探测（那会把 native 构建误判成交
叉编译，AC_RUN_IFELSE 全跳过、生成错误 config.h），改的是探测脚本本身。
补丁新增行零平台宏（R8/PF5 口径：能力判定不靠 __OHOS__）。

上游无自动化测试（实测，非假设）：Makefile.am 与 man/Makefile.am 无
TESTS/check_PROGRAMS/check-local；configure 成功后 `make -n check` 只展开
check-recursive 骨架、`make check` 实跑 rc=0 且子目录 "Nothing to be done"。
test_package 因此自造真实断言（6 条，全部零成本可跑：-version/-help/缩写
/未知参数/缺参/无 DISPLAY 干净报错，均取自 XOpenDisplay 之前的代码路径，
声明数 ≤ 实测数，见 test_package/MANIFEST.yml）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XrefreshConan(ConanFile):
    name = "xrefresh"
    version = "1.1.0"
    description = ("Small X utility that forces the X server to repaint every "
                   "window by mapping a full-screen window over them")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xrefresh"
    url = "https://gitlab.freedesktop.org/xorg/app/xrefresh"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 构建/链接期依赖
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # 运行期闭包（libX11.so.6 的 DT_NEEDED 链，见模块 docstring）
        self.requires("libxcb/1.16", run=True)
        self.requires("libxau/1.0.11", run=True)
        self.requires("libxdmcp/1.1.5", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_dirs(self, name):
        """取依赖包的 include/lib 目录（不猜路径，直接读 cpp_info）。"""
        dep = self.dependencies[name]
        inc = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
        libdirs = dep.cpp_info.libdirs or ["lib"]
        lib = os.path.join(dep.package_folder, libdirs[0])
        return inc, lib

    def generate(self):
        tc = AutotoolsToolchain(self)
        x11_inc, x11_lib = self._dep_dirs("libx11")
        # xorgproto 的头在 include/X11/ 下，.pc 在 share/pkgconfig（不是 lib/）
        proto_inc, _ = self._dep_dirs("xorgproto")
        # PKG_CHECK_MODULES 走 pkg.m4 的文档化逃逸口：XREFRESH_CFLAGS 与
        # XREFRESH_LIBS 非空即直接采用、根本不调用 pkg-config（configure 第
        # 11681/11697 行 `if test -n "$XREFRESH_CFLAGS"` 分支；本包实测
        # `checking for XREFRESH... yes` 且 rc=0）。少依赖一个 pkg-config 可
        # 用性假设，也绕开 xproto.pc 落在 share/pkgconfig 的寻径差异；同族
        # xeyes 1.3.1（已合并）同款。
        tc.configure_args.append(
            f"XREFRESH_CFLAGS=-I{x11_inc} -I{proto_inc}")
        tc.configure_args.append(f"XREFRESH_LIBS=-L{x11_lib} -lX11")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS 在 conan 缓存的构建目录里 getcwd() 上溯父目录会失败
        # （实测首轮 conan create 报 `shell-init: error retrieving current
        # directory: getcwd: cannot access parent directories` →
        # `configure: error: working directory cannot be determined`，而目录本身
        # 完全可用：ls -di / cd / 路径查找都正常）。补丁已让 configure 顶部那段
        # `ac_pwd=`pwd` && ...` 在 pwd 失败时回退 $PWD；这里负责把 $PWD 摆成
        # 真正的构建目录——conan 只用 cwd= 传目录，继承来的 PWD 还是 conan CLI
        # 自己的位置，不修正就会指向错误的树（同族 xeyes 1.3.1 已合并同款处置）。
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游无测试套件可跑（0 用例，实测证据在 test_package/MANIFEST.yml），
        # 故此处不调 autotools.make(target="check")；实质验证在 test_package。

    def _sign_elf(self, path):
        """OHOS 内核可能拒绝未签名 ELF（同族 xeyes 处置）；签名工具不存在则跳过。

        先剥旧 .codesign 段再自签，幂等；chmod 容错（HMDFS chmod 能力为 0）。
        """
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for name in sorted(os.listdir(bin_dir)):
                self._sign_elf(os.path.join(bin_dir, name))

    def package_info(self):
        # 命令行工具：只对外提供 bin/（R38；纯库包才填 cpp_info.libs）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
