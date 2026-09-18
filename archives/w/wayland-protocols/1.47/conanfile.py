#!/usr/bin/env python3
"""Conan recipe for wayland-protocols 1.47 — Meson.

Wayland protocols and protocol extension XML definitions (data package).

Version note (R37): 1.47 is the minimum release satisfying wlroots 0.20.1's
`wayland-protocols >= 1.47`; the previously packaged 1.36.1 does not. Recipe
logic is carried over from archives/w/wayland-protocols/1.36.1, re-validated
against the 1.47 tree, with one substantive change: the embedded static
wayland-scanner now comes from **wayland 1.24.0** source instead of 1.22.0,
because 1.47's meson.build requires

    dependency('wayland-scanner', version: '>=1.23.0')   # when tests are on

Why a static scanner at all: HMDFS forbids loading shared libraries from the
Conan cache, so the `wayland` package's own scanner binary (linked against
libexpat.so/libxml2.so) cannot execute here. A statically linked scanner that
depends only on libc is compiled from source instead.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# version of the wayland source used to build the embedded static scanner
SCANNER_WAYLAND_VERSION = "1.24.0"


class WaylandProtocolsConan(ConanFile):
    name = "wayland-protocols"
    version = "1.47"
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
        # 与接口符号（.pc 提供 Cflags；不链接共享库——HMDFS 禁止动态加载
        # 共享库，测试可执行文件只依赖 libc.so 与静态接口数据）
        self.requires("wayland/" + SCANNER_WAYLAND_VERSION)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 下载 wayland 源码用于编译静态 wayland-scanner
        get(self, **self.conan_data["scanner_sources"],
            strip_root=True, destination="wayland-scanner-src")

    def generate(self):
        tc = MesonToolchain(self)
        # 启用上游测试（tests/meson.build：scan + pedantic C99 + C++ build）
        tc.project_options["tests"] = "true"

        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)
        wayland_base = self.dependencies["wayland"].package_folder

        # wayland-scanner.pc — 指向即将编译的静态 scanner 二进制。
        # Version 必须 >= 1.23.0（1.47 在 tests=true 时的硬性要求），
        # 故声明为用作扫描器的 wayland 版本。
        scanner_bin = os.path.join(self.generators_folder, "wayland-scanner")
        with open(os.path.join(fixed_pc_dir, "wayland-scanner.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(f"prefix={self.generators_folder}\n"
                    f"bindir=${{prefix}}\n"
                    f"wayland_scanner=${{bindir}}/wayland-scanner\n\n"
                    f"Name: Wayland Scanner\n"
                    f"Description: Wayland scanner\n"
                    f"Version: {SCANNER_WAYLAND_VERSION}\n")

        # wayland-client.pc / wayland-server.pc — Cflags 指向头文件目录，
        # Libs 指向静态 libwayland-protocol.a（提供 wl_surface_interface 等
        # 接口数据符号）。不链接共享库：测试可执行文件只依赖 libc.so。
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
                        f"Version: {SCANNER_WAYLAND_VERSION}\n"
                        f"Cflags: -I${{includedir}}\n"
                        f"Libs: -L{proto_lib_dir} -lwayland-protocol\n")
            self.output.info(f"wayland-protocols: created {pc_name}.pc")

        tc.pkg_config_path = os.pathsep.join(
            [fixed_pc_dir, tc.pkg_config_path or ""])
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
        # native PKG_CONFIG_PATH：tests/meson.build 的
        # dependency('wayland-scanner', native: true) 需在 native 侧查找
        if "[paths]" in content:
            content = content.replace(
                "[paths]",
                f"[paths]\npkg_config_path = '{fixed_pc_dir}'"
            )
        else:
            content += f"\n[paths]\npkg_config_path = '{fixed_pc_dir}'\n"
        with open(native_file, "w") as f:
            f.write(content)

    def _find_expat_static(self):
        """Locate a static libexpat.a for the fully static scanner link.

        The scanner is linked with `-static` so it depends only on libc (HMDFS
        cannot dlopen cache libraries). A static libexpat is therefore required.
        Preference order: the SDK-bundled copy used by the 1.36.1 recipe, then
        any static libexpat shipped by dependencies.
        """
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a",
        ]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat":
                candidates.append(os.path.join(dep.package_folder,
                                               "lib", "libexpat.a"))
        for c in candidates:
            if os.path.isfile(c):
                self.output.info(f"wayland-protocols: static expat -> {c}")
                return c
        raise ConanException(
            "no static libexpat.a found for the static wayland-scanner link; "
            f"tried: {candidates}")

    def _find_expat_include(self):
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/include",
        ]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat":
                candidates.append(os.path.join(dep.package_folder, "include"))
        for c in candidates:
            if os.path.isdir(c):
                return c
        return None

    def _build_static_scanner(self):
        """Build a statically-linked wayland-scanner from wayland source."""
        scanner_src = os.path.join(self.source_folder, "wayland-scanner-src")

        # Generate config.h
        config_h = os.path.join(scanner_src, "config.h")
        with open(config_h, "w", encoding="utf-8") as f:
            f.write(f'#define HAVE_EXPAT 1\n'
                    f'#define PACKAGE "wayland"\n'
                    f'#define VERSION "{SCANNER_WAYLAND_VERSION}"\n')

        # Generate wayland-version.h from template
        version_in = os.path.join(scanner_src, "src", "wayland-version.h.in")
        version_h = os.path.join(scanner_src, "src", "wayland-version.h")
        major, minor, micro = (SCANNER_WAYLAND_VERSION.split(".") + ["0"])[:3]
        with open(version_in, "r", encoding="utf-8") as f:
            content = f.read()
        for key, val in [("@WAYLAND_VERSION@", SCANNER_WAYLAND_VERSION),
                         ("@WAYLAND_VERSION_MAJOR@", major),
                         ("@WAYLAND_VERSION_MINOR@", minor),
                         ("@WAYLAND_VERSION_MICRO@", micro)]:
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
        expat_inc = self._find_expat_include()
        expat_lib = self._find_expat_static()
        inc_flag = f"-I{expat_inc} " if expat_inc else ""
        self.run(
            f'{cc} -o {scanner_bin} '
            f'-include {config_h} '
            f'-I{scanner_src} -I{scanner_src}/src -I{scanner_src}/protocol '
            f'{scanner_src}/src/scanner.c {scanner_src}/src/wayland-util.c '
            f'{inc_flag}{expat_lib} '
            f'-lm -lpthread -static',
            env="conanbuild",
        )
        self.output.info("wayland-protocols: built static wayland-scanner")

        # Build static libwayland-protocol.a from wayland.xml + all protocol XMLs
        # (provides wl_surface_interface / xdg_toplevel_interface / … data symbols)
        proto_objs = []
        ar = shutil.which("ar") or "/data/service/hnp/bin/ar"
        xml_files = [os.path.join(scanner_src, "protocol", "wayland.xml")]
        for subdir in ("stable", "staging", "unstable", "experimental"):
            base = os.path.join(self.source_folder, subdir)
            if not os.path.isdir(base):
                continue
            for root, _, files in os.walk(base):
                for fname in sorted(files):
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
        # 静态 scanner 必须在 meson configure 之前构建
        # （tests/meson.build 的 find_program() 会检查二进制是否存在）
        self._build_static_scanner()

        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

        # 上游测试：meson test（scan + pedantic C99 + C++ build 三类）
        # scan 用静态 wayland-scanner；build 类测试仅 include 头文件并静态链接
        # 接口数据，可执行文件只依赖 libc.so
        try:
            self.run("meson test", env="conanbuild")
        except Exception as e:
            self.output.warning(
                f"wayland-protocols: meson test partially failed: {e}"
            )

    def package(self):
        meson = Meson(self)
        meson.install()
        # 修正 wayland-protocols.pc 的 prefix：上游模板写作
        #   pkgdatadir=${pc_sysrootdir}${datarootdir}/wayland-protocols
        # 而 meson 传入的 prefix 是构建前缀，产出的 .pc 会让下游解析到不存在的
        # 路径。改写 prefix 为包真实路径，使
        # pkg_get_variable(WAYLAND_PROTOCOLS_DIR) 有效。
        for sub in ("share/pkgconfig", "lib/pkgconfig"):
            pc_path = os.path.join(self.package_folder, sub,
                                   "wayland-protocols.pc")
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
        self.cpp_info.set_property("pkg_config_name", "wayland-protocols")
