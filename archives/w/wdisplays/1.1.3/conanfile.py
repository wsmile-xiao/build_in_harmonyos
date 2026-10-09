#!/usr/bin/env python3
"""Conan recipe — wdisplays 1.1.3 (Wayland display configuration GUI, Meson).

wdisplays is a GTK+3 Wayland client that arranges outputs/monitors through
wlr-output-management-unstable-v1.  Adapted for OpenHarmony / HarmonyOS PC
(aarch64, clang 15, musl).

OHOS 适配要点（全部经本机实测，详见 notes.md）：
  - gtk/3.24.43 只有 broadway(HTML5) 后端：既没有 GDK Wayland 后端，也没有
    <gdk/gdkwayland.h>，而上游 wdisplays 依赖 GDK 的 Wayland 访问器。补丁
    0001 新增 src/gdkwayland-compat.{c,h}，用 wayland-client 真实
    wl_display_connect() 提供 wl_display/wl_output（wl_output 来自 registry
    绑定），Broadway 窗口没有 wl_surface 时返回 NULL，main.c/overlay.c 对
    NULL 做安全降级；同时把 meson 的 “GDK 必须有 wayland 后端” 硬断言放宽为
    “wayland 或 broadway 二者之一”
  - wayland-scanner：OHOS 制品仓 wayland 包的 bin/wayland-scanner 带
    构建机绝对路径 DT_NEEDED 且未签名（HMFS 直接执行 EPERM）——staging 时
    把绝对 DT_NEEDED 改写为 soname、重签名，并用 wrapper 注入
    LD_LIBRARY_PATH（glade/gtk 同款手法）
  - gnome.compile_resources 需要 glib-compile-resources（glib 包 bin/ 内
    OHOS ELF）——staging + 重签名 + 注入 gio-2.0.pc 的 glib_compile_resources
    变量
  - wayland-protocols 的 pkgdatadir 变量由 .pc 承载，注入 PkgConfigDeps
    生成的 wayland-protocols.pc；gdk-3.0.pc 由 PkgConfigDeps 不生成
    （gtk 配方无 gdk 组件），手工生成（targets=broadway）
  - glib-2.0.pc 补 -lintl（glib 2.84 的 g_libintl_* 在 libintl.so）
  - OHOS 下对 bin/ ELF 自签名（HMFS 未签名 ELF 不可执行）

上游测试：无（仓库无 tests/ 目录，meson.build 无 test() 注册，无 CI 测试
workflow）——见 notes.md 的核验证据表与 build() 输出的
HMBS_UPSTREAM_TEST_RESULT 标记。
"""
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, check_sha256, copy,
                               export_conandata_patches, get, unzip)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")
PATCHELF = os.path.join(HNP_BIN, "patchelf")
PYTHON3 = os.path.realpath(sys.executable)


class WdisplaysConan(ConanFile):
    name = "wdisplays"
    version = "1.1.3"
    description = ("GTK+3 Wayland client for arranging displays through "
                   "wlr-output-management-unstable-v1")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/artizirk/wdisplays"
    url = "https://github.com/artizirk/wdisplays"
    topics = ("wayland", "gtk", "display", "wlr-output-management")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wdisplays 1.1.3 only supports Linux/OHOS, got {self.settings.os}")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "wdisplays on OHOS only supports armv8 (aarch64)")

    def requirements(self):
        # meson.build: dependency('gtk+-3.0'), dependency('gdk-3.0'),
        # dependency('wayland-client'), dependency('wayland-protocols'),
        # dependency('epoxy')（libepoxy 经 gtk 传递进入 graph）
        self.requires("gtk/3.24.43", transitive_headers=True,
                      transitive_libs=True)
        self.requires("wayland/1.22.0", transitive_headers=True,
                      transitive_libs=True)
        self.requires("wayland-protocols/1.36")
        # expat 版本冲突：wayland/1.22.0 requires expat/2.8.2，gtk 链用
        # expat/2.8.2.1——override 统一为 gtk 链的 2.8.2.1（同上游，patch 级
        # 兼容；hyprpicker/0.4.7 同族冲突的先例）
        self.requires("expat/2.8.2.1", override=True)

    def build_requirements(self):
        # meson 从 ohpcd 工具包取（glade / libavtp 同款），不依赖 worker 全局
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    # ──────────────────────────────────────────────────────────────
    # source
    # ──────────────────────────────────────────────────────────────
    def source(self):
        sources = dict(self.conan_data["sources"])
        staged = os.path.expanduser("~/tmp/builds/wdisplays-1.1.3.tar.gz")
        if os.path.isfile(staged):
            # 本地 W3：优先消费已验证 sha256 的暂存 tarball（glade 同款），
            # CI 无暂存文件时走官方 URL 下载
            check_sha256(self, staged, sources["sha256"])
            unzip(self, staged, strip_root=True)
        else:
            get(self, **sources, strip_root=True)
        apply_conandata_patches(self)

    # ──────────────────────────────────────────────────────────────
    # generate
    # ──────────────────────────────────────────────────────────────
    def generate(self):
        PkgConfigDeps(self).generate()
        tools_folder = self._stage_elf_tools()
        self._augment_glib_pkg_config(tools_folder)
        self._create_gdk_pc()
        self._patch_libintl()
        self._augment_wayland_protocols_pc()
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "default_library": "shared",
        })
        tc.generate()
        self._inject_meson_tools(tools_folder)
        # 构建环境（工具 PATH / LD_LIBRARY_PATH / TMPDIR）随 conanbuild 脚本
        self._build_environment().vars(self).save_script("wdisplays_build_env")

    def _tool_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _stage_elf_tools(self):
        """Staging 构建期 OHOS ELF 工具（wayland-scanner / glib-compile-*）。

        实测（本机 aarch64 OHOS）：
        1. wayland 包 bin/wayland-scanner 直接执行报 EPERM（HMFS 未签名
           ELF 不可执行）；且其 DT_NEEDED 记录构建机绝对路径
           （.../.cache/conan2/p/expat.../lib/libexpat.so），loader 不查
           LD_LIBRARY_PATH——需 patchelf 改写为 soname。
        2. patchelf 会破坏签名，必须“拷贝 → 改写 → 重签名”的顺序。
        3. wrapper 脚本注入 LD_LIBRARY_PATH（依赖包真实 lib 目录）+ 工具目录
           本身在 PATH 最前，meson find_program() 命中 wrapper。
        """
        tools_folder = self._tool_folder()
        os.makedirs(tools_folder, exist_ok=True)
        lib_dirs = []
        for dep in self.dependencies.host.values():
            if dep.package_folder is None:
                continue
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    lib_dirs.append(libdir)

        staged = {}
        for dep_name, tool in (("wayland", "wayland-scanner"),
                               ("glib", "glib-compile-resources")):
            dep = self.dependencies.host.get(dep_name)
            if dep is None or dep.package_folder is None:
                continue
            src = os.path.join(dep.package_folder, "bin", tool)
            if not os.path.isfile(src):
                self.output.warning(f"{tool} not found in {dep_name}: {src}")
                continue
            staged[tool] = self._stage_elf_tool(src, tools_folder, tool, lib_dirs)

        # 工具目录置顶 PATH：meson find_program() + gnome 模块都吃 PATH
        env = Environment()
        env.prepend_path("PATH", tools_folder)
        env.vars(self).save_script("wdisplays_tools_env")
        return tools_folder

    def _stage_elf_tool(self, src, tools_folder, name, lib_dirs):
        real = os.path.join(tools_folder, f"{name}.elf")
        if not (os.path.isfile(real) and os.access(real, os.X_OK)):
            shutil.copyfile(src, real)
            os.chmod(real, 0o755)
            if os.path.isfile(PATCHELF):
                needed = self._absolute_needed(real)
                for entry in needed:
                    self.run(f"{shlex.quote(PATCHELF)} --replace-needed "
                             f"{shlex.quote(entry)} {shlex.quote(os.path.basename(entry))} "
                             f"{shlex.quote(real)}")
            if str(self.settings.os) == "OHOS":
                self._resign_elf(real)
        wrapper = os.path.join(tools_folder, name)
        q = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
        with open(wrapper, "w", encoding="utf-8", newline="\n") as h:
            h.write("#!/bin/sh\n")
            if lib_dirs:
                h.write("export LD_LIBRARY_PATH="
                        + ":".join(lib_dirs) + "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\n")
            h.write(f"exec {q(real)} \"$@\"\n")
        os.chmod(wrapper, 0o755)
        return wrapper

    def _absolute_needed(self, binary):
        """列出 ELF 中以绝对路径记录的 DT_NEEDED（构建机缓存路径残留）。"""
        readelf = os.path.join(HNP_BIN, "llvm-readelf")
        if not os.path.isfile(readelf):
            return []
        try:
            out = subprocess.run([readelf, "-d", binary], capture_output=True,
                                 text=True).stdout
        except Exception:
            return []
        return re.findall(r"NEEDED.*Shared library: \[(/[^\]]+)\]", out)

    def _resign_elf(self, binary):
        """HMFS 执行限制规避：移除 .codesign 段后 selfSign 重签（glade 同款）。"""
        if os.path.isfile(OBJCOPY):
            self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                     f"{shlex.quote(binary)} 2>/dev/null || true")
        if os.path.isfile(SIGN_TOOL):
            self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                                 "-outFile", binary, "-selfSign", "1"]))

    def _augment_glib_pkg_config(self, tools_folder):
        """glib 包内工具在 pc 里以变量暴露；PkgConfigDeps 生成的 pc 不含它
        们，meson 的 gnome 模块（compile_resources）需要
        gio-2.0 的 glib_compile_resources 变量。"""
        tools = {
            "glib-2.0": {
                "glib_mkenums": os.path.join(tools_folder, "glib-mkenums"),
                "glib_genmarshal": os.path.join(tools_folder, "glib-genmarshal"),
            },
            "gio-2.0": {
                "glib_compile_resources": os.path.join(tools_folder, "glib-compile-resources"),
            },
        }
        for pc_name, variables in tools.items():
            pc = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(pc):
                continue
            content = open(pc, encoding="utf-8").read()
            block = ""
            for key, value in variables.items():
                if f"{key}=" in content:
                    continue
                if not os.path.isfile(value):
                    continue
                block += f"{key}={value.replace(os.sep, '/')}\n"
            if block and "\nName:" in content:
                content = content.replace("\nName:", f"\n{block}\nName:", 1)
                open(pc, "w", encoding="utf-8", newline="\n").write(content)

    def _create_gdk_pc(self):
        """上游 src/meson.build 用 dependency('gdk-3.0') 读取 targets；gtk
        配方未声明 gdk 组件，PkgConfigDeps 不生成 gdk-3.0.pc，手工补一个
        （glade 同款；OHOS 上 GDK 后端为 broadway）。"""
        gtk = self.dependencies.host["gtk"]
        prefix = gtk.package_folder.replace(os.sep, "/")
        pc = os.path.join(self.generators_folder, "gdk-3.0.pc")
        with open(pc, "w", encoding="utf-8", newline="\n") as h:
            h.write(f"prefix={prefix}\n")
            h.write("exec_prefix=${prefix}\n")
            h.write("libdir=${prefix}/lib\n")
            h.write("includedir=${prefix}/include\n\n")
            h.write("targets=broadway\n\n")
            h.write("Name: GDK\n")
            h.write("Description: GTK+ Drawing Kit\n")
            h.write(f"Version: {gtk.ref.version}\n")
            h.write("Requires: gtk+-3.0\n")
            h.write("Libs: -L${libdir} -lgdk-3\n")
            h.write("Cflags: -I${includedir}/gtk-3.0\n")

    def _augment_wayland_protocols_pc(self):
        """protocol/meson.build 读 wayland-protocols 的 pkgdatadir；注入生成的
        .pc（指向包内 share/wayland-protocols）。"""
        dep = self.dependencies.host.get("wayland-protocols")
        if dep is None or dep.package_folder is None:
            return
        pc = os.path.join(self.generators_folder, "wayland-protocols.pc")
        if not os.path.isfile(pc):
            return
        pkgdatadir = os.path.join(dep.package_folder, "share",
                                  "wayland-protocols").replace(os.sep, "/")
        content = open(pc, encoding="utf-8").read()
        if "pkgdatadir=" in content:
            return
        content = content.replace("\nName:",
                                  f"\npkgdatadir={pkgdatadir}\ndatarootdir="
                                  f"{pkgdatadir}\nName:", 1)
        open(pc, "w", encoding="utf-8", newline="\n").write(content)

    def _patch_libintl(self):
        """glib 2.84 的 g_libintl_* 符号在 libintl.so（glib 包内）；
        PkgConfigDeps 生成的 glib-2.0.pc Libs 缺 -lintl。"""
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            return
        content = open(pc, encoding="utf-8").read()
        if "-lintl" in content:
            return
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Libs:") and "-lintl" not in line.split():
                line = line.rstrip("\r\n") + " -lintl\n"
            lines.append(line)
        open(pc, "w", encoding="utf-8", newline="\n").write("".join(lines))

    def _inject_meson_tools(self, tools_folder):
        """meson machine file 注入 ar/ranlib/pkg-config/ninja 绝对路径
        （OHOS 上裸名 subprocess 查找 ENOENT，glade 同款）。"""
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        cdir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if cdir:
            if not ar:
                cand = os.path.join(cdir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
            if not ranlib:
                cand = os.path.join(cdir, "llvm-ranlib")
                if os.path.isfile(cand):
                    ranlib = cand
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        ninja = shutil.which("ninja") or os.path.join(HNP_BIN, "ninja")
        for fn in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, fn)
            if not os.path.isfile(nf):
                continue
            content = open(nf, encoding="utf-8").read()
            if "[binaries]" not in content:
                continue
            binaries = []
            if ar and "\nar = " not in content:
                binaries.append(f"ar = '{ar}'")
            if ranlib and "\nranlib = " not in content:
                binaries.append(f"ranlib = '{ranlib}'")
            if pkg_config and ("\npkg-config = " not in content
                               and "\npkgconfig = " not in content):
                binaries.append(f"pkg-config = '{pkg_config}'")
            if ninja and os.path.isfile(ninja) and "\nninja = " not in content:
                binaries.append(f"ninja = '{ninja}'")
            if not binaries:
                continue
            content = content.replace("[binaries]\n",
                                      "[binaries]\n" + "\n".join(binaries) + "\n", 1)
            open(nf, "w", encoding="utf-8", newline="\n").write(content)

    def _build_environment(self):
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        for dep in self.dependencies.host.values():
            if dep.package_folder is None:
                continue
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir):
                env.prepend_path("PATH", bindir)
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        # 最后 prepend ⇒ 工具目录排在 PATH 最前，覆盖依赖包 bin/ 里的原始
        # 工具（wayland 包 bin/wayland-scanner 在 HMFS 上直接执行 EPERM）
        env.prepend_path("PATH", self._tool_folder())
        ninja = shutil.which("ninja") or os.path.join(HNP_BIN, "ninja")
        if os.path.isfile(ninja):
            env.define("NINJA", ninja)
        return env

    # ──────────────────────────────────────────────────────────────
    # build / package
    # ──────────────────────────────────────────────────────────────
    def build(self):
        env = self._build_environment()
        with env.vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            self._report_upstream_tests()

    def _report_upstream_tests(self):
        """上游无自动化测试（核验证据见 notes.md）。输出机器可读标记，
        供 W4/CI 消费；test_package 另行承担消费者视角测试。"""
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "N/A (upstream ships no test entry point)",
            "discovered": 0, "executed": 0, "passed": 0,
            "failed": 0, "skipped": 0,
            "reason": ("audit: 1.1.3 source tree has no tests/ directory, "
                       "meson.build registers no test() target and the repo "
                       "has no test workflow"),
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        print(msg, flush=True)
        self.output.info(msg)

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """OHOS 产物签名（ci/artifacts/sign.sh 同款自签；HMFS 未签名 ELF
        不可执行）。"""
        if not os.path.isfile(SIGN_TOOL):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        targets = []
        for pattern in (os.path.join(self.package_folder, "bin", "*"),
                        os.path.join(self.package_folder, "lib", "**", "*.so"),
                        os.path.join(self.package_folder, "lib", "**", "*.so.*")):
            targets.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(targets)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            for _round in (1, 2):
                self._resign_elf(binary)

    def package_info(self):
        # 应用包：只交付 bin/wdisplays 与 share/（.desktop、图标、GResource）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "wdisplays")
