#!/usr/bin/env python3
"""Conan recipe — xclicker 1.5.1 (Meson, GTK3 + X11/XTest).

XClicker 是一个基于 GTK3 与 X11 XTest/XInput2 的高速图形化自动点击器。
上游构建系统为 Meson（根 Makefile 只是 meson+ninja 的薄封装）。

OHOS (aarch64-linux-ohos) 适配要点：
  - 构建系统: 走上游 meson.build（裸 Makefile 不参与构建）
  - 显示栈: gtk/3.24.43（OHOS 上为 broadway 后端）+ libx11/libxi/libxtst
    OHOS 二进制；点击动作经 XTest/XInput2 直接与 X 服务器交互
  - gnome.compile_resources 需要构建期工具 glib-compile-resources：
    制品仓 glib 包的 bin 工具未签名，按 gtk/gdk-pixbuf 既有方案从
    glib 包复制到构建目录、OHOS 下签名，并注入 meson machine file
    的 [binaries]（否则 meson 报 could not get pkg-config variable）
  - 上游 src/meson.build 的 executable() 未声明 install:true，
    `meson install` 不落地产物 —— package() 显式拷贝构建产物到 bin/
  - OHOS 下对 bin/xclicker 签名（未签名不可执行）
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, check_sha256, copy,
                               export_conandata_patches, get, unzip)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

_GLIB_TOOL = "glib-compile-resources"
_SIGNER = "/data/service/hnp/bin/binary-sign-tool"


class XClickerConan(ConanFile):
    name = "xclicker"
    version = "1.5.1"
    description = ("XClicker — fast GUI autoclicker for X11 desktops "
                   "(GTK3 UI + XTest/XInput2)"
                   )
    license = "GPL-3.0-only"
    homepage = "https://github.com/robiot/xclicker"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # OHOS 二进制均已发布（W0 预检通过）；gtk 携带 UI 头文件与 X11 后端
        # 之外的 GUI 依赖，X11/XTest 头文件分别来自 libx11/libxi/libxtst。
        # X11 家族在本制品仓使用 .so 主版本命名（libX11.so.6.4.0 → libx11/6.4.0），
        # libxi/libxtst 的 6.1.0 与之同源对齐（libxi/1.8.3 等旧 ref 会拉入
        # libx11/6.4.0 造成版本冲突）。
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxi/6.1.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxtst/6.1.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        # 本地网络对 codeload 限速严重；本地已预取时直接复用（sha256 校验后）。
        # CI 上该文件不存在，走 get() 官方源（CI 自动添加镜像 fallback）。
        staged = os.path.expanduser("~/tmp/builds/xclicker-1.5.1.tar.gz")
        if os.path.isfile(staged):
            check_sha256(self, staged, sources["sha256"])
            unzip(self, staged, strip_root=True)
            return
        get(self, **sources, strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tools_folder = self._prepare_glib_tools()
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "warning_level": "2",
        })
        tc.generate()
        self._inject_meson_tools(tools_folder)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        src = os.path.join(self.build_folder, "src")
        dst = os.path.join(self.package_folder, "bin")
        copied = copy(self, self.name, src, dst)
        if not copied:
            raise ConanException(
                f"built executable not found in {src} (expected {self.name})")
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    # ── 构建期 GLib 工具（gnome.compile_resources）─────────────────────

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_glib_tools(self):
        """复制 glib 的 glib-compile-resources 到构建目录（OHOS 下签名）。

        制品仓 glib 包只签名 .so，不签名 bin 工具；而 meson 的 gnome 模块
        （gnome.compile_resources）在 configure 阶段即调用该工具
        （--generate-dependencies），未签名不可执行。
        """
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        src = os.path.join(glib_bin, _GLIB_TOOL)
        if not os.path.isfile(src):
            raise ConanException(f"GLib build tool missing: {src}")
        dst = os.path.join(tools_folder, _GLIB_TOOL)
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o755)
        if self.settings.os == "OHOS" and os.path.isfile(_SIGNER):
            self._sign_elf(dst)
        return tools_folder

    def _inject_meson_tools(self, tools_folder):
        """把静态链接器 / pkg-config / glib-compile-resources 写入 machine file。

        MesonToolchain 只在 [binaries] 里写 c/cpp；ar/ranlib 由 meson 自行
        探测 clang 默认的 `llvm-ar`/`llvm-ranlib`，而 conan 构建 env 的 PATH
        未必包含 SDK bin，导致 "Unknown linker(s): [['llvm-ar']]"。
        glib-compile-resources 则由 gnome 模块经 lookup_binary_entry 解析。
        一律改为绝对路径显式注入，消除对 PATH 的隐式依赖。
        """
        glib_tool = os.path.join(tools_folder, _GLIB_TOOL).replace(os.sep, "/")
        entries = {
            _GLIB_TOOL: glib_tool,
            "ar": self._resolve_tool(("ar",), ("llvm-ar", "ar")),
            "ranlib": self._resolve_tool(("ranlib",), ("llvm-ranlib", "ranlib")),
            "pkg-config": (self.conf.get("tools.gnu:pkg_config", default=None)
                           or shutil.which("pkg-config") or shutil.which("pkgconf")
                           or ""),
        }
        for fn in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            path = os.path.join(self.generators_folder, fn)
            if not os.path.isfile(path):
                continue
            content = open(path, encoding="utf-8").read()
            if "[binaries]" not in content:
                continue
            added = []
            for key, value in entries.items():
                if not value:
                    continue
                value = str(value).replace(os.sep, "/")
                if f"\n{key} =" in content:
                    # 已有（可能是不带路径的裸名）——替换为绝对路径
                    lines = []
                    for line in content.splitlines(keepends=True):
                        if line.startswith(f"{key} =") or line.startswith(f"{key}="):
                            line = f"{key} = '{value}'\n"
                        lines.append(line)
                    content = "".join(lines)
                else:
                    added.append(f"{key} = '{value}'")
            if added:
                content = content.replace("[binaries]\n",
                                          "[binaries]\n" + "\n".join(added) + "\n", 1)
            open(path, "w", encoding="utf-8", newline="\n").write(content)

    def _resolve_tool(self, conf_keys, names):
        """按 conf → SDK bin（编译器同目录）→ PATH 的顺序解析工具绝对路径。"""
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        for key in conf_keys:
            if ce.get(key):
                return ce[key]
        cc = ce.get("c") or ce.get("cpp") or ""
        cdir = os.path.dirname(cc) if os.path.sep in cc else ""
        for name in names:
            if cdir:
                cand = os.path.join(cdir, name)
                if os.path.isfile(cand):
                    return cand
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return ""

    # ── 构建环境 ──────────────────────────────────────────────────────

    def _build_environment(self):
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        # glib-compile-resources 依赖 glib/gio/.so；运行期需能找到依赖库
        glib_folder = self.dependencies["glib"].package_folder
        env.prepend_path("PATH", os.path.join(glib_folder, "bin"))
        env.prepend_path("PATH", self._glib_tools_folder())
        # SDK bin（clang/ninja/llvm-* 同目录）：meson 后端与工具探测需要
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        cc = ce.get("c") or ce.get("cpp") or ""
        if os.path.sep in cc:
            sdk_bin = os.path.dirname(cc)
            if os.path.isdir(sdk_bin):
                env.prepend_path("PATH", sdk_bin)
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    # ── OHOS ELF 签名 ────────────────────────────────────────────────

    def _sign_installed_elfs(self):
        if not os.path.isfile(_SIGNER):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        objcopy = self._find_objcopy()
        for binary in sorted(
                p for p in glob.glob(os.path.join(self.package_folder, "bin", "*"))
                if os.path.isfile(p) and not os.path.islink(p)):
            if objcopy:
                self.run(f"{shlex.quote(objcopy)} --remove-section .codesign "
                         f"{shlex.quote(binary)} 2>/dev/null || true")
            self._sign_elf(binary)

    def _find_objcopy(self):
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        cc = ce.get("c") or ""
        candidates = []
        if cc and os.path.sep in cc:
            candidates.append(os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        candidates.append("/data/service/hnp/bin/llvm-objcopy")
        candidates.append(shutil.which("llvm-objcopy"))
        return next((p for p in candidates if p and os.path.isfile(p)), None)

    def _sign_elf(self, binary):
        self.run(shlex.join([_SIGNER, "sign", "-inFile", binary,
                             "-outFile", binary, "-selfSign", "1"]))
