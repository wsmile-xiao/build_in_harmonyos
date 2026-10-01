#!/usr/bin/env python3
"""Conan test_package for wayland-protocols 1.48 — 消费者端到端测试（E2E）。

消费链与真实下游一致（kwayland / plasma-wayland-protocols 同款）：

1. 取得 wayland 1.24.0 源码（优先复用主配方 source() 已下载的 scanner
   源码，规避 CI 对 gitlab.freedesktop.org 的第二次下载请求被 429 限流；
   取不到才回退下载），编译静态 wayland-scanner（主配方同款：
   HMDFS 禁止动态加载共享库，scanner 必须 -static、仅依赖 libc）；
2. 用该 scanner 对包内 7 个代表协议 XML 生成 client-header + private-code
   （stable ×2 / staging ×3 含 1.48 唯一进入安装集的新协议
   xdg-session-management / unstable ×2；上游 1.48 meson.build 的
   installed_protocol_files 仅 stable/staging/unstable，experimental
   设计不安装，3 个 experimental 新协议由上游 191 项测试覆盖），并生成
   闭包——wayland.xml 私有代码提供 wl_surface/wl_seat/wl_output 等核心
   接口符号，xdg_toplevel 引用由同批 xdg-shell 提供；
3. 编译链接 consumer_e2e.c，运行时逐例核验编译态接口数据与包内 XML
   定义一致（接口名 / 版本号 / 请求计数 / XML 原样包含 name 与 version
   属性）。7 用例 × 4 检查点 = 28 项，任一失败退出码 1。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get

SCANNER_WAYLAND_VERSION = "1.24.0"
SCANNER_WAYLAND_URL = ("https://gitlab.freedesktop.org/wayland/wayland/"
                       "-/archive/1.24.0/wayland-1.24.0.tar.gz")
SCANNER_WAYLAND_SHA256 = \
    "7800858844751fc7113d7df3678dc6b58b26a056176a65c49a059763045bffd5"

# 7 个代表协议：stable ×2 / staging ×3（含 1.48 唯一进入安装集的新协议
# xdg-session-management）/ unstable ×2。全部取自安装集（上游
# installed_protocol_files = stable+staging+unstable，experimental 设计
# 不安装——真机实测包内无 experimental/ 目录）。
PROTOCOLS = [
    ("stable/xdg-shell/xdg-shell.xml", "xdg-shell"),
    ("stable/viewporter/viewporter.xml", "viewporter"),
    ("staging/xdg-session-management/xdg-session-management-v1.xml",
     "xdg-session-management-v1"),
    ("staging/xdg-activation/xdg-activation-v1.xml", "xdg-activation-v1"),
    ("staging/xdg-dialog/xdg-dialog-v1.xml", "xdg-dialog-v1"),
    ("unstable/xdg-decoration/xdg-decoration-unstable-v1.xml",
     "xdg-decoration-unstable-v1"),
    ("unstable/xdg-output/xdg-output-unstable-v1.xml",
     "xdg-output-unstable-v1"),
]


class WaylandProtocolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 对齐真实下游（kwayland 同款）：wayland 包提供 wayland-util.h
        # 等头文件；scanner 源码与本包主配方同源下载（1.24.0）。
        self.requires("wayland/" + SCANNER_WAYLAND_VERSION)

    # 注意: conan 2.29 对 in-place test_package 不调用 source()
    # （真机实测: 主配方 source() 执行而 test_package 的跳过）,
    # 故下载放 build() 开头, 经 get() 落盘到 build_folder。

    def _pkgdatadir(self):
        pkg = self.dependencies["wayland-protocols"].package_folder
        return self._resolve_pkgdatadir(pkg)

    @staticmethod
    def _resolve_pkgdatadir(pkg):
        """消费 wayland-protocols.pc：解析 VAR=value 行、递归展开 ${var}。

        package() 已把 .pc 的 prefix 改写为包真实路径，故
        pkgdatadir = ${prefix}/share/wayland-protocols 可直接定位。
        """
        pc = None
        for sub in ("share/pkgconfig", "lib/pkgconfig"):
            candidate = os.path.join(pkg, sub, "wayland-protocols.pc")
            if os.path.isfile(candidate):
                pc = candidate
                break
        if not pc:
            raise ConanException("wayland-protocols.pc not found in package")
        vars = {}
        with open(pc, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    vars[k.strip()] = v.strip()
        for _ in range(8):
            changed = False
            for k in list(vars):
                for kk, vv in vars.items():
                    nv = vars[k].replace("${" + kk + "}", vv)
                    if nv != vars[k]:
                        vars[k] = nv
                        changed = True
            if not changed:
                break
        pkgdatadir = vars.get("pkgdatadir", "")
        pkgdatadir = re.sub(r"\$\{[^}]+\}", "", pkgdatadir)
        if not pkgdatadir or not os.path.isdir(pkgdatadir):
            raise ConanException(
                f"pkgdatadir invalid: {pkgdatadir!r}")
        return pkgdatadir

    def _find_expat_static(self):
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a",
        ]
        if "expat" in self.dependencies:
            candidates.append(os.path.join(
                self.dependencies["expat"].package_folder, "lib", "libexpat.a"))
        for c in candidates:
            if os.path.isfile(c):
                return c
        raise ConanException(
            f"no static libexpat.a found for the static wayland-scanner link; "
            f"tried: {candidates}")

    def _find_expat_include(self):
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/include",
        ]
        if "expat" in self.dependencies:
            candidates.append(os.path.join(
                self.dependencies["expat"].package_folder, "include"))
        for c in candidates:
            if os.path.isdir(c):
                return c
        return None

    def _build_scanner(self):
        """主配方同款：wayland 1.24.0 源码 -static 编译 wayland-scanner。"""
        src = os.path.join(self.build_folder, "wayland-src")

        config_h = os.path.join(src, "config.h")
        with open(config_h, "w", encoding="utf-8") as f:
            f.write(f'#define HAVE_EXPAT 1\n'
                    f'#define PACKAGE "wayland"\n'
                    f'#define VERSION "{SCANNER_WAYLAND_VERSION}"\n')

        version_in = os.path.join(src, "src", "wayland-version.h.in")
        version_h = os.path.join(src, "src", "wayland-version.h")
        major, minor, micro = (SCANNER_WAYLAND_VERSION.split(".") + ["0"])[:3]
        with open(version_in, encoding="utf-8") as f:
            content = f.read()
        for key, val in [("@WAYLAND_VERSION@", SCANNER_WAYLAND_VERSION),
                         ("@WAYLAND_VERSION_MAJOR@", major),
                         ("@WAYLAND_VERSION_MINOR@", minor),
                         ("@WAYLAND_VERSION_MICRO@", micro)]:
            content = content.replace(key, val)
        with open(version_h, "w", encoding="utf-8") as f:
            f.write(content)

        dtd_h = os.path.join(src, "src", "wayland.dtd.h")
        self.run(
            f'python3 {src}/src/embed.py '
            f'{src}/protocol/wayland.dtd wayland_dtd > {dtd_h}',
            env="conanbuild",
        )

        scanner_bin = os.path.join(self.build_folder, "wayland-scanner")
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        expat_inc = self._find_expat_include()
        expat_lib = self._find_expat_static()
        inc_flag = f"-I{expat_inc} " if expat_inc else ""
        self.run(
            f'{cc} -o {scanner_bin} '
            f'-include {config_h} '
            f'-I{src} -I{src}/src -I{src}/protocol '
            f'{src}/src/scanner.c {src}/src/wayland-util.c '
            f'{inc_flag}{expat_lib} '
            f'-lm -lpthread -static',
            env="conanbuild",
        )
        return scanner_bin

    def _obtain_wayland_src(self):
        """wayland 1.24.0 源码取得（source() 对 in-place test_package 不被调用）。

        优先复用主配方 source() 已下载的 scanner 源码：被测试包在 conan
        缓存中的 package_folder 与 source_folder 是同一 p/<hash>/ 下的
        p/ 与 s/ 兄弟目录，主配方的 source() 把 scanner 源码解压在
        s/wayland-scanner-src。同一 run 内直接复制复用，避免 test_package
        对 gitlab.freedesktop.org 的第二次请求——CI 实测该第二次下载被
        429 限流（主配方的第一次下载成功），conan-build-test 挂
        FileNotFoundError wayland-src/config.h。取不到（跨缓存布局差异）
        才回退 get() 下载（sha256 校验）。
        """
        dst = os.path.join(self.build_folder, "wayland-src")
        dep_pkg = self.dependencies["wayland-protocols"].package_folder
        sibling = os.path.join(os.path.dirname(dep_pkg), "s",
                               "wayland-scanner-src")
        if (os.path.isfile(os.path.join(sibling, "src", "scanner.c"))
                and os.path.isfile(os.path.join(sibling, "protocol",
                                                "wayland.xml"))):
            shutil.copytree(sibling, dst)
            self.output.info("wayland-scanner source reused from main "
                             "recipe source folder (no re-download)")
            return dst
        get(self, SCANNER_WAYLAND_URL, sha256=SCANNER_WAYLAND_SHA256,
            strip_root=True, destination=dst)
        return dst

    def build(self):
        # wayland 1.24.0 源码（优先复用主配方 source() 的下载，规避 CI 二次下载 429）
        wayland_src = self._obtain_wayland_src()
        scanner = self._build_scanner()
        gen = os.path.join(self.build_folder, "gen")
        os.makedirs(gen, exist_ok=True)
        pkgdatadir = self._pkgdatadir()

        # 7 个代表协议：client-header + private-code
        for xml_rel, stem in PROTOCOLS:
            xml = os.path.join(pkgdatadir, xml_rel)
            self.run(f'{scanner} client-header --strict '
                     f'"{xml}" "{gen}/{stem}-client-protocol.h"',
                     env="conanbuild")
            self.run(f'{scanner} private-code --strict '
                     f'"{xml}" "{gen}/{stem}-protocol.c"',
                     env="conanbuild")

        # 闭包：wayland.xml 核心接口（wl_surface/wl_seat/wl_output 等；
        # xdg_toplevel 引用由同批 xdg-shell 提供）
        self.run(f'{scanner} private-code --strict '
                 f'"{wayland_src}/protocol/wayland.xml" '
                 f'"{gen}/wayland-protocol.c"',
                 env="conanbuild")

        # wayland-util.h 优先取 wayland 包 include（真实消费者形态），
        # 回退 scanner 源码树
        wayland_inc = os.path.join(
            self.dependencies["wayland"].package_folder, "include")
        if not os.path.isdir(wayland_inc):
            wayland_inc = os.path.join(wayland_src, "src")

        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        srcs = [os.path.join(self.source_folder, "src", "consumer_e2e.c"),
                f"{gen}/wayland-protocol.c"]
        srcs += [f"{gen}/{stem}-protocol.c" for _, stem in PROTOCOLS]
        self.run(f'{cc} -o {self.build_folder}/consumer_e2e '
                 f'-I{gen} -I{wayland_inc} -I{wayland_src}/src '
                 f'{" ".join(srcs)}',
                 env="conanbuild")

    def test(self):
        pkgdatadir = self._pkgdatadir()
        self.run(f'{self.build_folder}/consumer_e2e "{pkgdatadir}"',
                 env="conanrun")
        self.output.info("wayland-protocols consumer E2E PASS "
                         "(7 用例 × 4 检查点 = 28 项)")
