#!/usr/bin/env python3
"""Conan recipe — playerctl 2.4.1 (meson)

MPRIS D-Bus 媒体播放器控制器：
  * `playerctl`  — CLI 工具（play/pause/metadata/--follow/--format 等）
  * `playerctld` — 守护进程（跟踪当前活动播放器）
  * `libplayerctl.so` — 公共 C 库（playerctl.h，消费方可链接）

OHOS 适配要点
-------------
* 上游仅依赖 GLib/GObject/GIO（gio-unix-2.0），无 gudev / 无 Linux 专有
  syscall / 无 glibc 专有宏 → 源码零补丁（patches/ 为空）。
  `export_sources()` / `apply_conandata_patches()` 仍保留为补丁管道入口
  （G1 配方完整性要求；conandata.yml 的 patches 为空映射，两处均为空操作）。
* meson 构建期需要 glib 的 codegen 工具（gdbus-codegen / glib-mkenums）。
  MesonToolchain 不把宿主机依赖的 bin/ 放上 PATH，故 generate() 里：
    - 为 glib 的 python 工具生成 wrapper（runpy 定位脚本本体，解决
      share/glib-2.0 资源定位）；
    - 把 glib_mkenums / gdbus_codegen 变量注入生成的 .pc，
      meson 的 gnome.gdbus_codegen()/gnome.mkenums_simple() 由此解析工具。
* glib 配方只导出 glib-2.0/gobject-2.0/gio-2.0 三个 .pc；上游 meson.build
  还要 dependency('gio-unix-2.0') → 生成转发型 gio-unix-2.0.pc。
* MesonToolchain 不写 ar/ranlib/pkg-config 到 native file（OHOS 的 llvm-ar
  不在 PATH），_inject_meson_binaries() 补全。
* OHOS 下 conan 子进程无法直接执行位于 HMDFS 的脚本（E232/E055，Error 126）。
  conan Meson helper 硬编码 `meson <args>`，而 meson 包 bin/meson 是
  `#!/bin/sh` 脚本 → run() 内仅在 OHOS 分支改写为
  `<python> <meson.py> <args>`（仓库既有惯用法，见 archives/a/abx/0.1 的
  autotools 版与 knowledge/doc/E232.md）。
* 鸿蒙 PC XPM 要求被 exec 的 ELF 代码签名 → package() 对 bin/ 与 lib/ 下的
  ELF 用 binary-sign-tool 自签（工具缺失时告警不阻塞，兼容 cross Docker）。
* 构建沙箱不支持 symlink/link 系统调用（见 _ensure_shared_lib_aliases），
  meson 会跳过全部符号链接 → package() 用实体文件补齐
  libplayerctl.so / libplayerctl.so.<major>。
"""

import glob
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

_OHOS_BIN = "/data/service/hnp/bin"
_OHOS_OBJCOPY = _OHOS_BIN + "/llvm-objcopy"
_OHOS_SIGNER = _OHOS_BIN + "/binary-sign-tool"


class PlayerctlConan(ConanFile):
    name = "playerctl"
    version = "2.4.1"
    description = "MPRIS media player controller (CLI tools + C library)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/altdesktop/playerctl"
    url = ""

    # CLI 工具包（产出 bin/playerctl、bin/playerctld）→ R38 需软件级 commands.json
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # conandata.yml 的 patches 为空映射（上游源码零补丁），此处为空操作；
        # 保留 G1 要求的补丁管道入口，后续如需上游补丁只需填 patches。
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # glib 提供 glib-2.0 / gobject-2.0 / gio-2.0 / gio-unix-2.0（仅这一个直接依赖）
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # CI worker / 本机 PATH 均无 meson，走 conan 制品仓（R36 已发布）
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    # ── generate ────────────────────────────────────────────────────────────
    def generate(self):
        PkgConfigDeps(self).generate()
        self._ensure_gio_unix_pc()
        self._augment_pc_with_glib_tools()

        tc = MesonToolchain(self)
        # 依赖一律走 conan，禁止 meson 偷偷下载 wrap 子项目
        tc.project_options["wrap_mode"] = "nodownload"
        # OHOS 无 gtk-doc（gtkdoc-scan 不存在）→ 否则 meson configure 直接 error
        tc.project_options["gtk-doc"] = "false"
        # OHOS 无 gobject-introspection-1.0 → 关闭 GIR 生成（上游默认 true）
        tc.project_options["introspection"] = "false"
        tc.project_options["bash-completions"] = "false"
        tc.project_options["zsh-completions"] = "false"
        tc.generate()
        self._inject_meson_binaries()

    def _find_in_deps(self, *relative):
        for dependency in self.dependencies.host.values():
            folder = dependency.package_folder
            if not folder:
                continue
            candidate = os.path.join(folder, *relative)
            if os.path.exists(candidate):
                return candidate
        return None

    def _create_python_tool_wrapper(self, tool_name):
        """glib 的 gdbus-codegen / glib-mkenums 是 python 脚本，直接 exec 时
        __file__ 指向 bin/，无法定位 share/glib-2.0 下的 codegen 包。
        runpy.run_path 保留脚本本体路径，等价于 `python3 <tool>`。"""
        tool_path = self._find_in_deps("bin", tool_name)
        if not tool_path:
            return "${bindir}/" + tool_name
        wrapper = os.path.join(self.generators_folder, tool_name + "-python")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#!%s\n"
                "import runpy\n"
                "import sys\n"
                "sys.argv = [%r] + sys.argv[1:]\n"
                "runpy.run_path(%r, run_name='__main__')\n"
                % (sys.executable, tool_path, tool_path)
            )
        os.chmod(wrapper, 0o755)
        return wrapper.replace("\\", "/")

    def _augment_pc_with_glib_tools(self):
        """meson 的 gnome.gdbus_codegen()/gnome.mkenums_simple() 先在 PATH 找
        gdbus-codegen / glib-mkenums，找不到则回退读 .pc 变量；这里把变量写进
        PkgConfigDeps 生成的 .pc，工具暴露不依赖 PATH 顺序。"""
        tools = {
            "glib-2.0": ["glib_mkenums=" + self._create_python_tool_wrapper("glib-mkenums")],
            "gobject-2.0": ["glib_mkenums=" + self._create_python_tool_wrapper("glib-mkenums")],
            "gio-2.0": ["gdbus_codegen=" + self._create_python_tool_wrapper("gdbus-codegen")],
        }
        for pc_name, entries in tools.items():
            pc_file = os.path.join(self.generators_folder, pc_name + ".pc")
            if not os.path.isfile(pc_file):
                self.output.warning("Could not augment missing %s" % pc_file)
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            missing = [e for e in entries if e.split("=", 1)[0] + "=" not in content]
            if not missing:
                continue
            addition = "\n" + "\n".join(missing)
            anchor = content.find("\nName:")
            if anchor >= 0:
                content = content[:anchor] + addition + content[anchor:]
            else:
                content = addition + "\n" + content
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _ensure_gio_unix_pc(self):
        """上游 meson.build: `dependency('gio-unix-2.0')`（无版本约束）。
        glib 配方导出的组件只有 gio-2.0，故生成转发型 .pc。"""
        target = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        if os.path.isfile(target):
            return
        source = os.path.join(self.generators_folder, "gio-2.0.pc")
        version = "2.84.0"
        if os.path.isfile(source):
            with open(source, encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("Version:"):
                        version = line.split(":", 1)[1].strip()
                        break
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "Name: GIO unix specific APIs\n"
                "Description: forwarding .pc generated by playerctl recipe\n"
                "Version: %s\n"
                "Requires: gio-2.0\n" % version
            )

    def _inject_meson_binaries(self):
        """MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进
        native file，也不写 pkg-config；meson 按裸名探测会失败（OHOS 的
        llvm-ar/llvm-ranlib 不在 PATH）。全路径注入 [binaries] 段。"""
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        cc = compilers.get("c") or ""
        bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
        ar, ranlib = compilers.get("ar"), compilers.get("ranlib")
        for directory in (bindir,
                          "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"):
            if not ar and directory:
                candidate = os.path.join(directory, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
            if not ranlib and directory:
                candidate = os.path.join(directory, "llvm-ranlib")
                if os.path.isfile(candidate):
                    ranlib = candidate
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append("ar = '%s'" % ar)
            if ranlib and "\nranlib =" not in content:
                insert.append("ranlib = '%s'" % ranlib)
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append("pkg-config = '%s'" % pkg_config)
            if not insert:
                continue
            content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
            with open(machine_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    # ── OHOS：脚本必须以「解释器 + 脚本」形式调用 ───────────────────────────
    def _resolve_meson_launcher(self):
        """定位 meson 的 python 入口，返回 (python, meson.py) 全路径，失败返回 None。

        conan 的 Meson helper 把命令硬编码为 `meson <args>`（conan/tools/meson/
        meson.py，无官方挂钩）。而 conan meson 包的 bin/meson 是
        `#!/bin/sh` 脚本：

            #!/bin/sh
            here=$(CDPATH= cd "$(dirname "$0")" && pwd)
            exec python3 "$here/../lib/python3.12/site-packages/meson.py" "$@"

        OHOS 下 conan 子进程经 posix_spawn 直接执行 HMDFS 上的脚本被内核拒绝，
        报 `/system/bin/sh: <pkg>/bin/meson: Permission denied` + Error 126
        （knowledge/doc/E232.md、E055）。改为 `<python> <meson.py> <args>`
        绕开 shebang：python3 与 meson.py 均由 conan 侧显式指定，不再依赖
        exec 位。仓库既有惯用法见 archives/a/abx/0.1（autotools 版）。
        """
        try:
            dependency = self.dependencies.build["meson"]
        except Exception:
            return None
        folder = getattr(dependency, "package_folder", None)
        if not folder:
            return None
        entries = sorted(glob.glob(os.path.join(folder, "lib", "python3*",
                                               "site-packages", "meson.py")))
        python = sys.executable
        if not entries or not python or not os.path.isfile(python):
            return None
        return python, entries[0]

    @property
    def _meson_launcher(self):
        if not hasattr(self, "_meson_launcher_cached"):
            self._meson_launcher_cached = self._resolve_meson_launcher()
        return self._meson_launcher_cached

    def run(self, command, *args, **kwargs):
        """OHOS 分支把 `meson <args>` 改写为 `<python> <meson.py> <args>`。

        仅改写 Meson helper 生成的前缀命令；其余 self.run（签名工具、objcopy）
        原样透传。非 OHOS 平台（Linux CI worker）保持 conan 原生行为。
        """
        if (isinstance(command, str) and command.startswith("meson ")
                and self.settings.os == "OHOS"):
            launcher = self._meson_launcher
            if launcher:
                rewritten = shlex.join(list(launcher) + shlex.split(command)[1:])
                self.output.info("OHOS meson launcher: %s" % rewritten)
                command = rewritten
        return super().run(command, *args, **kwargs)

    # ── build / package ─────────────────────────────────────────────────────
    def build(self):
        # 上游无 meson test() 目标；上游测试是独立 pytest 套件（test/），
        # 需 session D-Bus + python 依赖，不在 conan build() 内运行（见 notes.md）。
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        self._ensure_shared_lib_aliases()
        self._sign_artifacts()

    def _ensure_shared_lib_aliases(self):
        """补齐共享库的链接名与 SONAME 文件。

        构建沙箱内 symlinkat()/linkat() 被内核拒绝（实测 `ln -s` → exit 1、
        os.link → EPERM，而 cp/copy2 正常），meson install 因此打印
        "Symlink creation does not work on this platform. Skipping all
        symlinking." 并跳过全部符号链接，lib/ 只剩 libplayerctl.so.2.4.1。
        消费方 `-lplayerctl`（playerctl.pc 的 Libs）找不到 libplayerctl.so、
        运行时按 SONAME（libplayerctl.so.2）加载也会失败。
        平台既有产出形态即为实体文件（已发布的 glib 包中
        libglib-2.0.so / .so.0 / .so.0.8400.0 三个同尺寸实体文件），故此处
        在别名缺失时用实体文件补齐；meson 能正常建链的环境不产生任何改动。
        """
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        real = [p for p in glob.glob(os.path.join(libdir, "libplayerctl.so.*"))
                if not os.path.islink(p)]
        if not real:
            return
        source = sorted(real)[-1]
        major = os.path.basename(source)[len("libplayerctl.so."):].split(".")[0]
        for alias in ("libplayerctl.so." + major, "libplayerctl.so"):
            target = os.path.join(libdir, alias)
            if os.path.lexists(target):
                continue
            shutil.copy2(source, target)
            self.output.info(
                "Materialized shared library alias %s (symlinks unsupported)"
                % os.path.basename(target))

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_artifacts(self):
        """鸿蒙 PC XPM：被 exec 的可执行文件/动态库需代码签名。"""
        targets = []
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                path = os.path.join(bindir, name)
                if os.path.isfile(path) and not os.path.islink(path):
                    targets.append(path)
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for pattern in ("**/*.so", "**/*.so.*"):
                targets.extend(glob.glob(os.path.join(libdir, pattern), recursive=True))
        targets = [t for t in targets if self._is_elf(t)]
        if not targets:
            return
        signer = _OHOS_SIGNER
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        objcopy = _OHOS_OBJCOPY if os.path.isfile(_OHOS_OBJCOPY) else shutil.which("llvm-objcopy")
        for target in sorted(set(targets)):
            if objcopy:
                self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true'
                         % (objcopy, target))
            self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                     % (signer, target, target))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "playerctl")
        self.cpp_info.libs = ["playerctl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # playerctl.h 直接 include <glib-object.h>/<glib.h>，消费方需要 glib 头
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
