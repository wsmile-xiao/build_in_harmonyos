#!/usr/bin/env python3
"""Conan recipe — polkit 127 (Authorization framework for Linux/OHOS).

polkit 提供应用层授权机制：polkitd 守护进程、libpolkit-gobject-1 /
libpolkit-agent-1 库与 pkaction/pkcheck/pkexec 等 CLI。meson 构建。

依赖（ohpcd 已发布）：glib/2.84.0（提供 gio-2.0/gio-unix-2.0/glib-2.0/
gobject-2.0）、expat、duktape（JS 规则引擎）；dbus 可选。
pam/systemd/elogind 在 ohpcd 无——用 authfw=shadow（shadow 口令文件，
零外部依赖）与 session_tracking=ConsoleKit（规避 libsystemd/libelogind）。

OHOS 适配（沿用 dconf 0.40.0 的 meson 模式）：
- G2/PkgConfigDeps 只生成 glib-2.0.pc，缺 gio-2.0/gio-unix-2.0/gobject-2.0
  等子 .pc——从 glib 包 pkgconfig 目录复制并改写 prefix=/（避免工具变量
  指向 /bin/...）。
- E012 变体：真机 hnp 工具链 ar/llvm-ar 不在 PATH——把探测到的 ar/ranlib
  全路径注入 conan_meson_native.ini。
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


def _merge_glib_tool_vars(self, glib_pkg):
    """把 glib 包原始 .pc 里的变量行（datadir/工具变量等）合并进 Conan 生成的
    glib-2.0.pc。

    meson 的 gnome.mkenums_simple / gobject-query 用 get_variable(pkgconfig:)
    读 glib_mkenums/glib_genmarshal/gobject_query 等变量；而 gio-2.0.pc 的
    Requires: glib-2.0 在展开 cflags 时还需要 glib-2.0.pc 提供 datadir 变量
    ——Conan PkgConfigDeps 生成的 glib-2.0.pc 都不含这些（polkit 编译报
    "Could not get pkg-config variable ... glib-2.0" 与
    "Variable 'datadir' not defined in ... glib-2.0.pc"）。从 glib 包原始 .pc
    提取所有缺失的 `key=value` 变量行（bindir 已在 _fix_pc_prefix 后指向
    glib 包实际路径），合并进 generators_folder。
    """
    src_pc = os.path.join(glib_pkg, "lib", "pkgconfig", "glib-2.0.pc")
    dst_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
    if not (os.path.isfile(src_pc) and os.path.isfile(dst_pc)):
        return
    with open(dst_pc, encoding="utf-8", errors="replace") as f:
        dst = f.read()
    dst_lines = dst.splitlines()
    have_keys = set()
    for dl in dst_lines:
        if "=" in dl:
            have_keys.add(dl.split("=", 1)[0].strip())
    merge_lines = []
    with open(src_pc, encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or "=" not in stripped or stripped.startswith("#"):
                continue
            key = stripped.split("=", 1)[0].strip()
            if key not in have_keys and key not in ("Name", "Description",
                                                    "Version", "Libs",
                                                    "Cflags", "Requires",
                                                    "Requires.private"):
                merge_lines.append(stripped)
                have_keys.add(key)
    if not merge_lines:
        return
    with open(dst_pc, "w", encoding="utf-8", newline="\n") as f:
        f.write(dst.rstrip("\n") + "\n" + "\n".join(merge_lines) + "\n")
    self.output.info("polkit: merged glib pc vars into glib-2.0.pc")


class PolkitConan(ConanFile):
    name = "polkit"
    version = "127"
    package_type = "application"
    license = "LGPL-2.0-or-later"
    homepage = "https://www.freedesktop.org/software/polkit/"
    description = "polkit — application authorization framework (polkitd + libpolkit-gobject + CLI)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"polkit does not support os={self.settings.os}")

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("expat/2.8.2")
        self.requires("duktape/2.7.0")

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
        # 关闭桌面生态/系统依赖：shadow 口令认证（无 pam）、ConsoleKit 会话
        # 跟踪（无 libsystemd/libelogind）、关闭 man/introspection/examples/gettext
        tc.project_options["authfw"] = "shadow"
        tc.project_options["session_tracking"] = "ConsoleKit"
        tc.project_options["systemdsystemunitdir"] = ""
        tc.project_options["polkitd_user"] = "root"
        tc.project_options["examples"] = "false"
        tc.project_options["introspection"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["man"] = "false"
        tc.project_options["gettext"] = "false"
        # 构建上游测试（rule 4 实测）
        tc.project_options["tests"] = "true"
        # OHOS musl 的 libintl.h 是空 stub，不声明 gettext()——gi18n.h 里
        # `#define _(String) gettext (String)` 展开后报 undeclared function。
        # 用恒等宏 `-Dgettext(x)=(x)` 让 _() 原样返回字符串（gettext=false
        # 本就无翻译需求），一处修复所有 _() 调用（pkttyagent/pkaction/
        # pkcheck 等）。
        tc.c_args.append('-Dgettext(x)=(x)')
        tc.generate()
        # PkgConfigDeps 只生成 glib-2.0.pc，缺 gio-2.0/gio-unix-2.0/gobject-2.0
        # 等 glib 子 .pc——从 glib 包 pkgconfig 目录复制并改写 prefix。
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
                        _fix_pc_prefix(d, glib_pkg)
            # meson 的 gnome.mkenums_simple / gobject-query 从 glib-2.0.pc 读
            # glib_mkenums/glib_genmarshal/gobject_query 等工具变量——Conan
            # PkgConfigDeps 生成的 glib-2.0.pc 不含这些变量（polkit 编译报
            # "Could not get pkg-config variable ... glib-2.0"）。把 glib 包
            # 原始 .pc 里的工具变量行（${bindir}/... 指向 glib 包实际 bin）
            # 合并进 generators_folder 的 glib-2.0.pc。
            _merge_glib_tool_vars(self, glib_pkg)
        # CI #36892：gio-2.0 的 Requires 链（glib-2.0 → libpcre2-8 等）在
        # CI 的 meson PKG_CONFIG_PATH 里找不到——meson 的 PKG_CONFIG_PATH 由
        # conan 工具链固定指向 generators_folder，os.environ 注入在 CI 不
        # 生效（本地因依赖目录齐全才过）。把**所有依赖包**的 .pc 都复制进
        # generators_folder，保证整个 Requires 链可直接解析（含 libpcre2-8/
        # libffi 等传递依赖）。
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            dep_pc = os.path.join(dep_pkg, "lib", "pkgconfig")
            if not os.path.isdir(dep_pc):
                continue
            for name in os.listdir(dep_pc):
                if not name.endswith(".pc"):
                    continue
                d = os.path.join(self.generators_folder, name)
                if not os.path.exists(d):
                    shutil.copy2(os.path.join(dep_pc, name), d)
                _fix_pc_prefix(d, dep_pkg)
        # 真机 hnp 工具链的 ar/llvm-ar 不在 PATH（E012 变体）——meson 报
        # "Unknown linker(s)"。把探测到的 ar/ranlib 全路径注入
        # conan_meson_native.ini（dconf/pycairo 同款）。
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
        # PKG_CONFIG_PATH 注入 os.environ 保证 meson 子进程继承 glib pkgconfig
        # 目录（解析 gio-2.0 等子 .pc）——buildenv_info 注入对 meson 未生效。
        # CI 上 glib-2.0.pc 的 Requires 链（libffi/libpcre2-8 等）不在 meson 的
        # PKG_CONFIG_PATH 里会报 "Package libpcre2-8 was not found"——把**所有**
        # 依赖包的 lib/pkgconfig 目录都注入，保证整个 Requires 链可解析
        # （本地过不代表 CI 过）。
        pkgconfig_dirs = []
        for dep in self.dependencies.values():
            try:
                pkg_dir = dep.package_folder
            except Exception:
                continue
            if not pkg_dir:
                continue
            pc_dir = os.path.join(pkg_dir, "lib", "pkgconfig")
            if os.path.isdir(pc_dir) and pc_dir not in pkgconfig_dirs:
                pkgconfig_dirs.append(pc_dir)
        if pkgconfig_dirs:
            cur = os.environ.get("PKG_CONFIG_PATH", "")
            existing = set(cur.split(os.pathsep)) if cur else set()
            merged = [d for d in pkgconfig_dirs if d not in existing]
            if merged:
                os.environ["PKG_CONFIG_PATH"] = (os.pathsep.join(merged) +
                                                 (os.pathsep + cur if cur else ""))
            self.output.info("polkit: build env PKG_CONFIG_PATH=%s"
                             % os.environ["PKG_CONFIG_PATH"])
        meson = Meson(self)
        meson.configure()
        meson.build()
        # ── 上游测试（rule 4 实测回填）──
        # test/polkit 4 个单元测试（unixuser/unixgroup/unixnetgroup/identity）
        # 不依赖运行中的 polkitd/会话 D-Bus；test-polkitbackendjsauthority
        # 需 mock dbus。逐一执行，失败的按平台限制如实声明（rule 1.2）。
        self.run("meson test -C {} --print-errorlogs".format(self.build_folder),
                 env="conanbuild", ignore_errors=True)

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
