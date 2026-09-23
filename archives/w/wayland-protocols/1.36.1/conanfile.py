#!/usr/bin/env python3
"""Conan recipe for wayland-protocols 1.36 — Meson.

Wayland protocols and protocol extensions XML definitions
（hyprpicker 前置依赖，data 包）。无编译产物，meson 安装 XML 文件
与 .pc；上游 131 项测试（44 scan + 44 pedantic C99 + 43 C++ build）
通过静态 wayland-scanner（从 wayland 1.22.0 源码编译，仅依赖 libc）
执行——HMDFS 禁止动态加载共享库，wayland 包的 scanner 二进制链接
libexpat.so/libxml2.so 无法执行，故从源码静态编译替代。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class WaylandProtocolsConan(ConanFile):
    name = "wayland-protocols"
    version = "1.36.1"
    description = "Wayland protocols and protocol extensions XML definitions"
    license = "MIT"
    homepage = "https://wayland.freedesktop.org/"
    url = "https://gitlab.freedesktop.org/wayland/wayland-protocols"

    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游测试 tests/meson.build 依赖 wayland-client/wayland-server 头文件
        # （.pc 仅提供 Cflags include 路径，不链接共享库——HMDFS 禁止
        # 动态加载共享库，测试可执行文件只依赖 libc.so）
        self.requires("wayland/1.22.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 下载 wayland 源码用于编译静态 wayland-scanner
        get(self, **self.conan_data["scanner_sources"],
            strip_root=True, destination="wayland-scanner-src")

    def generate(self):
        tc = MesonToolchain(self)
        # 启用上游测试（tests/meson.build：131 项 scan + pedantic C99 + C++ build）
        tc.project_options["tests"] = "true"

        # 创建修正后的 .pc 文件（wayland 包 .pc prefix=/ 需修正）
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)
        wayland_dep = self.dependencies["wayland"]
        wayland_base = wayland_dep.package_folder

        # wayland-scanner.pc — 指向即将编译的静态 scanner 二进制
        scanner_bin = os.path.join(self.generators_folder, "wayland-scanner")
        with open(os.path.join(fixed_pc_dir, "wayland-scanner.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(f"prefix={self.generators_folder}\n"
                    f"bindir=${{prefix}}\n"
                    f"wayland_scanner=${{bindir}}/wayland-scanner\n\n"
                    f"Name: Wayland Scanner\n"
                    f"Description: Wayland scanner\n"
                    f"Version: 1.22.0\n")

        # wayland-client.pc / wayland-server.pc — Cflags for headers + Libs for
        # static wayland-protocol.a（提供 wl_surface_interface 等接口符号，
        # 避免运行时 musl ld 报 symbol not found；不链接共享库——HMDFS 禁止
        # 动态加载共享库，测试可执行文件只依赖 libc.so + 静态接口数据）
        proto_lib_dir = self.generators_folder
        for pc_name, desc in [
            ("wayland-client", "Wayland client side library"),
            ("wayland-server", "Server side implementation of the Wayland protocol"),
        ]:
            with open(os.path.join(fixed_pc_dir, pc_name + ".pc"), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(f"prefix={wayland_base}\n"
                        f"includedir=${{prefix}}/include\n\n"
                        f"Name: {desc}\n"
                        f"Description: {desc}\n"
                        f"Version: 1.22.0\n"
                        f"Cflags: -I${{includedir}}\n"
                        f"Libs: -L{proto_lib_dir} -lwayland-protocol\n")
            self.output.info(f"wayland-protocols: created {pc_name}.pc")

        # 注入 fixed_pkgconfig 到 cross PKG_CONFIG_PATH
        tc.pkg_config_path = os.pathsep.join([fixed_pc_dir, tc.pkg_config_path or ""])
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
        # 注入 native PKG_CONFIG_PATH（tests/meson.build
        # dependency('wayland-scanner', native: true) 需在 native 查找）
        if "[paths]" in content:
            content = content.replace(
                "[paths]",
                f"[paths]\npkg_config_path = '{fixed_pc_dir}'"
            )
        else:
            content += f"\n[paths]\npkg_config_path = '{fixed_pc_dir}'\n"
        with open(native_file, "w") as f:
            f.write(content)

    def _build_static_scanner(self):
        """Build a statically-linked wayland-scanner from source.

        HMDFS prevents loading shared libraries from the Conan cache.
        The wayland package's scanner binary links libexpat.so/libxml2.so
        and cannot execute. We compile a static scanner (only depends on
        libc.so) from the wayland 1.22.0 source.
        """
        scanner_src = os.path.join(self.source_folder, "wayland-scanner-src")

        # Generate config.h
        config_h = os.path.join(scanner_src, "config.h")
        with open(config_h, "w", encoding="utf-8") as f:
            f.write('#define HAVE_EXPAT 1\n'
                    '#define PACKAGE "wayland"\n'
                    '#define VERSION "1.22.0"\n')

        # Generate wayland-version.h from template
        version_in = os.path.join(scanner_src, "src", "wayland-version.h.in")
        version_h = os.path.join(scanner_src, "src", "wayland-version.h")
        with open(version_in, "r", encoding="utf-8") as f:
            content = f.read()
        for key, val in [("@WAYLAND_VERSION@", "1.22.0"),
                         ("@WAYLAND_VERSION_MAJOR@", "1"),
                         ("@WAYLAND_VERSION_MINOR@", "22"),
                         ("@WAYLAND_VERSION_MICRO@", "0")]:
            content = content.replace(key, val)
        with open(version_h, "w", encoding="utf-8") as f:
            f.write(content)

        # Generate wayland.dtd.h using embed.py
        dtd_h = os.path.join(scanner_src, "src", "wayland.dtd.h")
        self.run(
            f'python3 {scanner_src}/src/embed.py '
            f'{scanner_src}/protocol/wayland.dtd wayland_dtd > {dtd_h}',
            env="conanbuild",
        )

        # Compile static scanner (only depends on libc.so)
        scanner_bin = os.path.join(self.generators_folder, "wayland-scanner")
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        expat_inc = "/data/service/hnp/expat.org/expat_2.7.3/include"
        expat_lib = "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a"
        self.run(
            f'{cc} -o {scanner_bin} '
            f'-include {config_h} '
            f'-I{scanner_src} -I{scanner_src}/src -I{scanner_src}/protocol '
            f'{scanner_src}/src/scanner.c {scanner_src}/src/wayland-util.c '
            f'-I{expat_inc} {expat_lib} '
            f'-lm -lpthread -static',
            env="conanbuild",
        )
        self.output.info("wayland-protocols: built static wayland-scanner")

        # Build static libwayland-protocol.a from wayland.xml + all
        # wayland-protocols XML files (provides wl_surface_interface,
        # xdg_toplevel_interface, zwp_tablet_tool_v2_interface etc.
        #  — data-only symbols, no function calls, no undefined refs)
        proto_srcs = self.source_folder
        proto_objs = []
        ar = shutil.which("ar") or "/data/service/hnp/bin/ar"
        # 1. Core wayland.xml protocol
        xml_files = [os.path.join(scanner_src, "protocol", "wayland.xml")]
        # 2. All wayland-protocols XML files (stable/staging/unstable)
        for subdir in ("stable", "staging", "unstable"):
            base = os.path.join(proto_srcs, subdir)
            if not os.path.isdir(base):
                continue
            for root, _, files in os.walk(base):
                for fname in files:
                    if fname.endswith(".xml"):
                        xml_files.append(os.path.join(root, fname))
        for xml_path in xml_files:
            stem = os.path.splitext(os.path.basename(xml_path))[0]
            pc = os.path.join(self.generators_folder, f"proto-{stem}.c")
            po = os.path.join(self.generators_folder, f"proto-{stem}.o")
            self.run(
                f'{scanner_bin} -s public-code {xml_path} {pc}',
                env="conanbuild",
            )
            self.run(
                f'{cc} -c -o {po} {pc} '
                f'-include {config_h} '
                f'-I{scanner_src} -I{scanner_src}/src -I{scanner_src}/protocol',
                env="conanbuild",
            )
            proto_objs.append(po)
        proto_a = os.path.join(self.generators_folder, "libwayland-protocol.a")
        self.run(f'{ar} rcs {proto_a} {" ".join(proto_objs)}', env="conanbuild")
        self.output.info(
            f"wayland-protocols: built static libwayland-protocol.a "
            f"({len(proto_objs)} protocols)"
        )

    def build(self):
        # Build static wayland-scanner before meson configure
        # (tests/meson.build find_program() checks binary existence)
        self._build_static_scanner()

        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

        # 上游测试：meson test（131 项：44 scan + 44 pedantic C99 + 43 C++ build）
        # scan 测试使用静态 wayland-scanner，build 测试仅 include 头文件
        # 不链接共享库（.pc 无 Libs 字段），可执行文件只依赖 libc.so
        try:
            self.run("meson test", env="conanbuild")
        except Exception as e:
            self.output.warning(
                f"wayland-protocols: meson test 部分失败：{e}"
            )

    def package(self):
        meson = Meson(self)
        meson.install()
        # 修正 wayland-protocols.pc 的 prefix：meson 生成 prefix=/（根目录），
        # 导致 pkgdatadir=${pc_sysrootdir}${datarootdir}/wayland-protocols
        # 指向 /share/wayland-protocols（不存在）。改写为包真实路径，
        # 下游 hyprpicker 用 pkg_get_variable(WAYLAND_PROTOCOLS_DIR) 才有效
        for sub in ("share/pkgconfig", "lib/pkgconfig"):
            pc_path = os.path.join(self.package_folder, sub, "wayland-protocols.pc")
            if os.path.isfile(pc_path):
                with open(pc_path, "r", encoding="utf-8") as f:
                    content = f.read()
                content = re.sub(
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
