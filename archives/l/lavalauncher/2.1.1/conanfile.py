#!/usr/bin/env python3
"""Conan recipe for lavalauncher 2.1.1 — Meson (C).

A simple and highly configurable launcher for Wayland.
Requires wayland/wayland-protocols/cairo/libxkbcommon (+librsvg 可选);
upstream no test target. wayland-scanner（wayland 包自带、链接共享库）
在 OHOS 沙箱 HMDFS 无法动态加载 → 按
DRAFT-ohos-static-tool-bypass-dlopen-limit 从 wayland 源码静态编译替代。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class LavalauncherConan(ConanFile):
    name = "lavalauncher"
    version = "2.1.1"
    description = "A simple and highly configurable launcher for Wayland"
    license = "GPL-3.0-or-later"
    homepage = "https://git.sr.ht/~leon_plickat/lavalauncher"
    url = "https://git.sr.ht/~leon_plickat/lavalauncher"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def requirements(self):
        # meson.build dependency() 直接引用（protocol/meson.build 另有
        # dependency('wayland-scanner', native: true) 工具依赖）
        self.requires("wayland/1.22.0")
        self.requires("wayland-protocols/1.36")
        self.requires("cairo/1.18.4")
        self.requires("libxkbcommon/1.6.0")
        self.requires("librsvg/2.62.3")
        # 传递依赖 .pc 被间接引用（wayland-client.pc Requires libffi、
        # cairo.pc Requires zlib/glib/pixman/fontconfig、glib-2.0.pc
        # Requires libpcre2-8 等），conan 会把纯传递依赖标为
        # "Skipped binaries" 不装二进制，导致 pkg-config 找不到 .pc——
        # 提升为直接 requires 强制安装（hyprpicker 同款）
        self.requires("libffi/3.4.4")
        self.requires("pcre2/10.45")
        # 版本冲突 override（与 lavalauncher-deps 探索生成器一致）：
        # libpng 依赖链引入 zlib/1.3.1.1.1.1 与 cairo 链的 1.3.1.1 冲突，
        # 统一为 1.3.1.1；fontconfig 链引入 expat/2.8.2.1 与 wayland 的
        # 2.8.2 冲突；gdk-pixbuf/librsvg 链引入 glib/2.88.0.1 与 cairo 链
        # 的 2.84.0.1 冲突；librsvg 链引入 libxml2/2.15.3.1 与 cairo 链
        # 的 2.15.3 冲突
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("expat/2.8.2", override=True)
        self.requires("glib/2.84.0.1", override=True)
        self.requires("libxml2/2.15.3", override=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = MesonToolchain(self)
        # OHOS 沙箱无文档构建依赖，禁用 man 页（option 名带连字符）
        tc.project_options["man-pages"] = "disabled"
        # 制品仓依赖 .pc prefix 可能指向构建路径（/conan2/p/b/.../p），
        # 复制改写 prefix 置顶（hyprpicker/wayland 同款）
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        pc_paths = []
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                self.output.info(f"WARN: dep {dep.ref} has no package_folder, skip pc injection")
                continue
            for pc_dir in ("lib", "share"):
                pc = os.path.join(dep.package_folder, pc_dir, "pkgconfig")
                if not os.path.isdir(pc):
                    continue
                pc_paths.append(pc)
                for pc_name in os.listdir(pc):
                    if not pc_name.endswith(".pc"):
                        continue
                    base = dep.package_folder
                    with open(os.path.join(pc, pc_name), "r",
                              encoding="utf-8") as f:
                        content = f.read()
                    content = re.sub(
                        r"(?m)^prefix=.*$", f"prefix={base}", content
                    )
                    content = re.sub(
                        r"(?m)^exec_prefix=.*$", f"exec_prefix={base}", content
                    )
                    content = re.sub(
                        r"(?m)^libdir=.*$", f"libdir={base}/lib", content
                    )
                    content = re.sub(
                        r"(?m)^includedir=.*$", f"includedir={base}/include",
                        content,
                    )
                    content = re.sub(
                        r"/[^\"\s]*/p/b/[^/\s]+/p",
                        base, content,
                    )
                    # cairo 源码头形式引用 <cairo/cairo.h>，但 cairo.pc
                    # Cflags 只给 -I${includedir}/cairo（缺 include 根），
                    # 补上 include 根目录（hyprpicker 同款问题，探索实测）
                    if pc_name == "cairo.pc":
                        content = re.sub(
                            r"Cflags:\s*-I\$\{includedir\}/cairo",
                            "Cflags: -I${includedir} -I${includedir}/cairo",
                            content,
                        )
                    os.makedirs(fixed_pc_dir, exist_ok=True)
                    with open(os.path.join(fixed_pc_dir, pc_name), "w",
                              encoding="utf-8", newline="\n") as f:
                        f.write(content)
        # 依赖真实 pkgconfig 路径注入（含 fixed_pkgconfig 置顶）
        if pc_paths:
            tc.pkg_config_path = os.pathsep.join(
                [fixed_pc_dir] + pc_paths
            )
        tc.generate()
        # OHOS 沙箱：meson 找不到 llvm-ar/ranlib，注入 native file
        # （wayland/zix/serd 先例）
        ar_path = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        ranlib_path = shutil.which("llvm-ranlib") or "/data/service/hnp/bin/llvm-ranlib"
        native_file = self.generators_folder + "/conan_meson_native.ini"
        with open(native_file) as f:
            content = f.read()
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nranlib = '{ranlib_path}'\nc ="
        )
        with open(native_file, "w") as f:
            f.write(content)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # 额外下载 wayland 源码，供静态编译 wayland-scanner 用
        get(self, **self.conan_data["scanner_sources"],
            strip_root=True, destination="wayland-scanner-src")

    def _find_expat_static(self):
        """按序查找 libexpat.a（SDK 自带 → 依赖包内），找不到显式报错。"""
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a",
        ]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat":
                p = os.path.join(dep.package_folder, "lib", "libexpat.a")
                if os.path.isfile(p):
                    candidates.append(p)
        for c in candidates:
            if os.path.isfile(c):
                return c
        raise ConanException(
            "lavalauncher: libexpat.a not found for static wayland-scanner"
        )

    def _find_expat_include(self):
        for c in [
            "/data/service/hnp/expat.org/expat_2.7.3/include",
        ]:
            if os.path.isfile(os.path.join(c, "expat.h")):
                return c
        for dep in self.dependencies.values():
            if dep.ref.name == "expat":
                p = os.path.join(dep.package_folder, "include")
                if os.path.isfile(os.path.join(p, "expat.h")):
                    return p
        raise ConanException(
            "lavalauncher: expat.h not found for static wayland-scanner"
        )

    def build(self):
        # wayland-scanner：从 wayland 源码静态编译（DRAFT 方案），
        # 必须在 meson.configure() 之前执行（find_program 检查存在性）
        self._build_static_scanner()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def _build_static_scanner(self):
        """静态编译 wayland-scanner 并写 wayland-scanner.pc 交给构建系统。"""
        src = os.path.join(self.source_folder, "wayland-scanner-src")
        scanner_bin_dir = os.path.join(self.build_folder, "scanner-bin")
        os.makedirs(scanner_bin_dir, exist_ok=True)
        scanner_bin = os.path.join(scanner_bin_dir, "wayland-scanner")
        if os.path.isfile(scanner_bin):
            self.output.info("lavalauncher: static wayland-scanner already built, skip")
        else:
            ver = "1.22.0"
            major, minor, micro = ver.split(".")
            # 由 .h.in 模板生成 wayland-version.h（脱离构建系统手工补齐）
            h_in = os.path.join(src, "src", "wayland-version.h.in")
            if os.path.isfile(h_in):
                with open(h_in, "r", encoding="utf-8") as f:
                    content = f.read()
                for key, val in [
                    ("@WAYLAND_VERSION@", ver),
                    ("@WAYLAND_VERSION_MAJOR@", major),
                    ("@WAYLAND_VERSION_MINOR@", minor),
                    ("@WAYLAND_VERSION_MICRO@", micro),
                ]:
                    content = content.replace(key, val)
                with open(os.path.join(src, "src", "wayland-version.h"), "w",
                          encoding="utf-8") as f:
                    f.write(content)
            expat_inc = self._find_expat_include()
            expat_lib = self._find_expat_static()
            cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
            self.run(
                f'{cc} -o {scanner_bin} '
                f'-I{src}/src '
                f'{src}/src/scanner.c {src}/src/wayland-util.c '
                f'-I{expat_inc} {expat_lib} -lm -lpthread -static',
                env="conanbuild",
            )
            self.output.info("lavalauncher: static wayland-scanner built")
        # wayland-scanner.pc 指向自编译工具（native 侧查找）；
        # 版本满足下游门槛（lavalauncher 无版本要求，取 wayland 1.22.0）
        pc_path = os.path.join(self.generators_folder,
                               "fixed_pkgconfig", "wayland-scanner.pc")
        with open(pc_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                f"prefix={scanner_bin_dir}\n"
                f"bindir=${{prefix}}\n"
                f"wayland_scanner=${{bindir}}/wayland-scanner\n"
                f"Name: wayland-scanner\n"
                f"Description: Wayland scanner (static, OHOS)\n"
                f"Version: 1.22.0\n"
            )
        self.output.info("lavalauncher: wayland-scanner.pc written to fixed_pkgconfig")

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # 可执行文件（R38：需 commands.json）
        self.cpp_info.bindirs = ["bin"]
