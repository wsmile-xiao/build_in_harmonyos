#!/usr/bin/env python3
"""Conan recipe for dconf — GNOME gsettings 后端 + dconf 命令行工具。

dconf 是 GNOME 的低层配置系统（GSettings 后端），C 实现，meson 构建。
产物：libdconf 库 + bin/dconf 命令行工具 + GSettings 后端模块 +
D-Bus service（dconf-service）。依赖 glib（提供 gio-2.0/gio-unix-2.0）
与 dbus（dbus-1，session bus service dir 探测），均已发布 ohpcd。
"""
import os
import re as _re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


def _fix_pc_prefix(pc_path, prefix):
    """Rewrite the .pc `prefix=` line to the given prefix (glib .pc 用 prefix=/
    导致工具变量指向 /bin/...，需改为实际包路径)."""
    if not os.path.isfile(pc_path):
        return
    data = open(pc_path, encoding="utf-8", errors="replace").read()
    data = _re.sub(r"(?m)^prefix=.*$", f"prefix={prefix}", data, count=1)
    open(pc_path, "w", encoding="utf-8").write(data)


class DconfConan(ConanFile):
    name = "dconf"
    version = "0.40.0"
    package_type = "application"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/Projects/dconf"
    description = "dconf — GNOME low-level configuration system (GSettings backend + dconf CLI)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"dconf does not support os={self.settings.os}")

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("dbus/1.14.10")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # meson 构建必须分离 source/build 目录（否则 "Source and build
        # directories must not be the same"）
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # 关闭 systemd/bash-completion/man/gtk-doc/vapi 等桌面生态依赖项
        tc.project_options["systemduserunitdir"] = ""
        tc.project_options["bash_completion"] = "false"
        tc.project_options["man"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["vapi"] = "false"
        tc.generate()
        # PkgConfigDeps 只生成 glib-2.0.pc，未生成 dconf 需要的 gio-2.0.pc /
        # gio-unix-2.0.pc（glib 包的子 pkg-config）；同样 dbus 包生成 dbus.pc
        # 而非 dconf 需要的 dbus-1.pc。meson 的 PKG_CONFIG_PATH 由 conan 工具链
        # 固定指向 generators_folder——把 glib/dbus 包 pkgconfig 目录下缺失的
        # .pc 复制过来，meson 才能解析 gio-2.0/dbus-1 依赖（G2 实测）。
        try:
            glib_pkg = self.dependencies["glib"].package_folder
        except Exception:
            glib_pkg = None
        if glib_pkg:
            src_pc = os.path.join(glib_pkg, "lib", "pkgconfig")
            if os.path.isdir(src_pc):
                for name in os.listdir(src_pc):
                    if name.endswith(".pc"):
                        s = os.path.join(src_pc, name)
                        d = os.path.join(self.generators_folder, name)
                        if not os.path.exists(d):
                            shutil.copy2(s, d)
                        # glib 的 .pc 里 prefix=/ 导致 ${bindir} 变成 /bin/...（如
                        # gdbus_codegen=//bin/gdbus-codegen 错误值）——改写 prefix
                        # 为 glib 实际包路径，meson 才能解析 gio 的工具变量。
                        _fix_pc_prefix(d, glib_pkg)
        try:
            dbus_pkg = self.dependencies["dbus"].package_folder
        except Exception:
            dbus_pkg = None
        if dbus_pkg:
            src_pc = os.path.join(dbus_pkg, "lib", "pkgconfig")
            if os.path.isdir(src_pc):
                for name in os.listdir(src_pc):
                    if name.endswith(".pc"):
                        s = os.path.join(src_pc, name)
                        d = os.path.join(self.generators_folder, name)
                        if not os.path.exists(d):
                            shutil.copy2(s, d)
        # dbus 包的 Conan 配方生成 dbus.pc，而 dconf 的 meson.build 用
        # dependency('dbus-1')——pkg-config 按文件名匹配查询键，复制 dbus.pc
        # 为 dbus-1.pc 供查询（内容 Libs: -ldbus-1 已正确）。
        gen_pc = os.path.join(self.generators_folder, "dbus.pc")
        gen_dbus1 = os.path.join(self.generators_folder, "dbus-1.pc")
        if os.path.isfile(gen_pc) and not os.path.exists(gen_dbus1):
            shutil.copy2(gen_pc, gen_dbus1)
        # 真机 hnp 工具链的 ar/llvm-ar 不在 PATH（E012 变体）——meson 报
        # "Unknown linker(s): [['llvm-ar-15'],['llvm-ar'],['ar'],['gar']]"。
        # 把探测到的 ar/ranlib 全路径注入 conan_meson_native.ini（pycairo 同款）。
        self._inject_meson_archiver()

    # --- 归档器探测（真机 hnp 工具链 ar 不在 PATH，须给 meson 绝对路径） ---
    def _probe_archiver(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or os.environ.get("CC") or ""
        bindir = os.path.dirname(cc) if (cc and ("/" in cc or os.path.sep in cc)) else ""
        dirs = []
        for d in (bindir, "/data/service/hnp/bin", "/data/service/hnp/llvm/bin",
                  os.path.expanduser("~/usr/local/bin")):
            if d and d not in dirs:
                dirs.append(d)
        cands = []
        for d in dirs:
            for n in ("llvm-ar", "llvm-ar-15", "ar"):
                p = os.path.join(d, n)
                if os.path.isfile(p):
                    cands.append(p)
        for n in ("llvm-ar", "llvm-ar-15", "ar", "gar"):
            p = shutil.which(n)
            if p:
                cands.append(p)
        seen, ar = set(), None
        for p in cands:
            if p not in seen:
                seen.add(p)
                ar = p
                break
        if not ar:
            return None, None
        base = os.path.dirname(ar)
        is_llvm = os.path.basename(ar).startswith("llvm")
        rl_names = ("llvm-ranlib", "ranlib") if is_llvm else ("ranlib", "llvm-ranlib")
        rl = None
        for n in rl_names:
            p = os.path.join(base, n)
            if os.path.isfile(p):
                rl = p
                break
        if not rl:
            for n in rl_names:
                p = shutil.which(n)
                if p:
                    rl = p
                    break
        return ar, rl

    def _inject_meson_archiver(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar, rl = ce.get("ar"), ce.get("ranlib")
        if not ar:
            ar, rl = self._probe_archiver()
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (ar and os.path.isfile(nf)):
            return
        with open(nf, encoding="utf-8") as f:
            content = f.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        ins = "[binaries]\nar = '%s'\n" % ar
        if rl:
            ins += "ranlib = '%s'\n" % rl
        with open(nf, "w", encoding="utf-8") as f:
            f.write(content.replace("[binaries]\n", ins, 1))

    def build(self):
        apply_conandata_patches(self)
        # buildenv_info 的 PKG_CONFIG_PATH 注入对 meson configure 未生效
        # （G2 实测 meson-log 里 PKG_CONFIG_PATH 仍只有 conan 目录）——直接注入
        # os.environ 保证 meson 子进程继承 glib pkgconfig 目录（解析 gio-2.0）。
        try:
            glib_pkg = self.dependencies["glib"].package_folder
        except Exception:
            glib_pkg = None
        if glib_pkg:
            pc_dir = os.path.join(glib_pkg, "lib", "pkgconfig")
            if os.path.isdir(pc_dir):
                cur = os.environ.get("PKG_CONFIG_PATH", "")
                if pc_dir not in cur.split(os.pathsep):
                    os.environ["PKG_CONFIG_PATH"] = pc_dir + (os.pathsep + cur if cur else "")
                self.output.info("dconf: build env PKG_CONFIG_PATH=%s"
                                 % os.environ["PKG_CONFIG_PATH"])
        meson = Meson(self)
        meson.configure()
        meson.build()
        # ── 上游测试（rule 4 实测回填）──
        # 真机实测：11 个单元/ABI 测试目标全部通过（无会话 D-Bus 依赖）——
        # paths/changeset/shm/gvdb/gdbus-thread/gdbus-filter/engine/client/
        # writer/libdconf/gsettings。
        # gdbus-thread-leak/gdbus-filter-leak 需会话 D-Bus（E002 /tmp 只读 +
        # GTestDBus 硬编码 /tmp socket 路径）；dconf 集成测试需 dbus-daemon。
        # 已实测构建 dbus-daemon + LD_PRELOAD bind shim 验证会话总线可启动，
        # 但 GTestDBus 握手机制在 OHOS 仍受限（详见 notes.md / manifest）。
        self.run(
            "meson test -C {} paths changeset shm gvdb gdbus-thread "
            "gdbus-filter engine client writer libdconf gsettings".format(self.build_folder),
            env="conanbuild",
        )

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
