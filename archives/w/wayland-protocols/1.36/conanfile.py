#!/usr/bin/env python3
"""Conan recipe for wayland-protocols 1.36 — Meson.

Wayland protocols and protocol extensions XML definitions
（hyprpicker 前置依赖，data 包）。无编译产物，meson 安装 XML 文件
与 .pc；无测试目标。1.36 含 hyprpicker 0.4.7 所需的 stable/linux-dmabuf、
stable/tablet、staging/fractional-scale、staging/cursor-shape 协议
（1.27 缺失，hyprwayland-scanner 报 "Couldn't load proto"）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class WaylandProtocolsConan(ConanFile):
    name = "wayland-protocols"
    version = "1.36"
    description = "Wayland protocols and protocol extensions XML definitions"
    license = "MIT"
    homepage = "https://wayland.freedesktop.org/"
    url = "https://gitlab.freedesktop.org/wayland/wayland-protocols"

    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = MesonToolchain(self)
        # data 包：禁用 tests（tests/meson.build 需 wayland-scanner 工具，
        # 本包不编译产物，无需测试）
        tc.project_options["tests"] = "false"
        tc.generate()
        # OHOS 沙箱：meson 找不到 llvm-ar，注入 native file（zix/serd 先例）
        ar_path = shutil.which("ar") or "/data/service/hnp/bin/ar"
        native_file = self.generators_folder + "/conan_meson_native.ini"
        with open(native_file) as f:
            content = f.read()
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nc ="
        )
        with open(native_file, "w") as f:
            f.write(content)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # 修正 wayland-protocols.pc 的 prefix：meson 生成 prefix=/（根目录），
        # 导致 pkgdatadir=${pc_sysrootdir}${datarootdir}/wayland-protocols
        # 指向 /share/wayland-protocols（不存在）。改写为包真实路径，
        # 下游 hyprpicker 用 pkg_get_variable(WAYLAND_PROTOCOLS_DIR) 才有效
        # （zix/serd/sord/avldrums .pc prefix 修正同款）。
        import re as _re
        for sub in ("share/pkgconfig", "lib/pkgconfig"):
            pc_path = os.path.join(self.package_folder, sub, "wayland-protocols.pc")
            if os.path.isfile(pc_path):
                with open(pc_path, "r", encoding="utf-8") as f:
                    content = f.read()
                content = _re.sub(
                    r"(?m)^prefix=.*$",
                    f"prefix={self.package_folder}",
                    content,
                )
                with open(pc_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
                self.output.info(
                    f"wayland-protocols: fixed {sub}/wayland-protocols.pc prefix"
                )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # .pc 提供 pkgdatadir（wayland-protocols 安装目录），
        # hyprpicker 用 pkg_get_variable(WAYLAND_PROTOCOLS_DIR)
        self.cpp_info.set_property("pkg_config_name", "wayland-protocols")
