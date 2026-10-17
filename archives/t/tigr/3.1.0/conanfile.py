#!/usr/bin/env python3
"""Conan recipe — tigr 3.1.0 (TIny GRaphics library, single-file C).

tigr 是一个单文件 C 图形库：核心为纯 framebuffer 库（位图、绘制原语、
文字渲染、PNG 读写），窗口/输入后端按平台分离（X11/GL/Win32/Cocoa/Android/iOS）。

OHOS 适配（R40 适配完整性）：
  - 以 `TIGR_HEADLESS` 模式编译：剔除 X11/GL 窗口与输入后端
    （OHOS 无 X11/GLX，窗口后端不适用），保留全部核心 framebuffer API
    （tigrBitmap/tigrClear/tigrPlot/tigrLine/tigrBlit/tigrPrint/tigrLoadImage/
    tigrSaveImage/tigrInflate 等），均为实质实现，无 stub。
  - 产物：libtigr.a（静态库）+ tigr.h；消费者 include <tigr.h> 链接 -ltigr。

来源：erkkah/tigr 官方 GitHub tag `v3.1.0` 官方 tag archive（codeload.github.com），
conandata.yml 带官方归档 SHA-256。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class TigrConan(ConanFile):
    name = "tigr"
    version = "3.1.0"
    package_type = "library"

    description = (
        "TIGR - TIny GRaphics library: a tiny cross-platform framebuffer "
        "graphics library in C with bitmap windows, drawing helpers, bitmap "
        "font text output and PNG loading/saving. Adapted for HarmonyOS in "
        "TIGR_HEADLESS mode (pure framebuffer core, no X11/GL window backend)."
    )
    homepage = "https://github.com/erkkah/tigr"
    license = "Unlicense"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("graphics", "framebuffer", "2d", "png", "single-file", "c")

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tigr headless core is supported only on Linux/OHOS"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # 官方源：erkkah/tigr 官方 tag `v3.1.0` 官方 tag archive。
        # strip_root=True 解包后源码根即仓库内容：tigr.c/tigr.h/src/examples/ci。
        # codeload 响应 Content-Type 为 application/zip，需显式 filename 后缀
        # 让解压按 .tar.gz 识别（否则被误判为 zip 抛 BadZipFile）。
        src = dict(self.conan_data["sources"])
        src["filename"] = "tigr-3.1.0.tar.gz"
        get(self, **src, strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器必须从 Conan conf 获取，禁止裸用 ${CC}/${CFLAGS}。
        comp = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)
        cc = comp.get("c", "clang")
        ar = comp.get("ar", "llvm-ar")
        ranlib = comp.get("ranlib", "llvm-ranlib")

        src = os.path.join(self.source_folder, "tigr.c")
        out = os.path.join(self.build_folder, "tigr.o")
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)

        # tigr 为单文件库：直接编译 amalgamated tigr.c。
        # -DTIGR_HEADLESS 剔除 X11/GL 窗口后端（OHOS 无 X11/GLX），保留纯
        # framebuffer 核心（绘图/文字/PNG/解压），全部为实质实现。
        flags = ["-DTIGR_HEADLESS", "-fPIC", "-O2"]
        if str(self.settings.build_type) == "Debug":
            flags = ["-DTIGR_HEADLESS", "-fPIC", "-g", "-O0"]
        self.run(f"{cc} {' '.join(flags)} -I{self.source_folder} -c {src} -o {out}")
        self.run(f"{ar} rcs {os.path.join(libdir, 'libtigr.a')} {out}")
        self.run(f"{ranlib} {os.path.join(libdir, 'libtigr.a')}")

        # 上游测试目标：ci/ci.c（TIGR_HEADLESS 最小补丁版，apply_conandata_patches
        # 已在 build() 开头应用 0001-ci-headless-guard.patch）。
        # 与库一致使用 -DTIGR_HEADLESS 编译；guard 已剔除窗口/GL/输入路径，
        # 保留纯 framebuffer 断言（offscreen/verifyDrawing/unicode）。
        ci_src = os.path.join(self.source_folder, "ci", "ci.c")
        if os.path.exists(ci_src):
            ci_bin = os.path.join(self.build_folder, "ci_headless")
            ci_run_dir = os.path.join(self.source_folder, "ci")
            self.run(
                f"{cc} {' '.join(flags)} -I{self.source_folder} {ci_src} "
                f"{src} -lm -o {ci_bin}"
            )
            # 运行目录为 ci/（5x7.png/ch.png/reference.png/../tigr.png 资源
            # 按相对路径加载）；失败即 raise，作为上游测试门禁。
            self.run(f"{ci_bin}", cwd=ci_run_dir)

    def package(self):
        inc = os.path.join(self.package_folder, "include")
        copy(self, "tigr.h", src=self.source_folder, dst=inc)

    def package_info(self):
        self.cpp_info.libs = ["tigr"]
        # 头less 模式下 tigr 依赖标准 C 库数学函数
        self.cpp_info.system_libs = ["m"]
