#!/usr/bin/env python3
"""Conan recipe — libdazzle 3.44.0 (meson).

GNOME libdazzle — GTK3 辅助/控件库（libdazzle-1.0.so）。
HarmonyOS PC (aarch64) 适配要点：
  - 构建系统: meson（conan-init 的 autotools 模板不适用）
  - 依赖: gio-2.0>=2.50 / gmodule-2.0 / gtk+-3.0>=3.22 + m/rt；对齐 ohpcd 已发布的
    gtk/3.24.43 依赖图（其 recipe pin glib/2.84.0.1），顶层用同一 glib 版本避免图内冲突
  - 关闭 with_introspection / with_vapi / enable_gtk_doc（需 g-ir-scanner、vala、gtk-doc）
  - enable_tools=false（dazzle-list-counters 是调试 CLI，纯库包不混装应用）
  - glib 构建工具（glib-mkenums / glib-compile-resources）经 tools 目录包装注入：
    python 脚本用 shell wrapper 调签名解释器执行（规避 HMDFS 对新解压脚本的
    execve 信任延迟），ELF 工具复制后自签；工具路径写进 glib-2.0.pc / gio-2.0.pc
    变量供 meson gnome 模块查询（同 gtk/3.24.43 实证范式）
  - 上游测试（tests/meson.build test() 注册 29 项）在 build() 真实执行：
    无显示环境用 gtk 包自带 broadwayd 提供 headless 显示后端
    （GDK_BACKEND=broadway，见 knowledge/drafts/DRAFT-headless-broadway-execute-upstream-gui-sample.md）
"""
import glob
import os
import shlex
import shutil
import subprocess
import time

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps

# tests/meson.build 中 test('…') 注册的上游测试套件（29 项注册名）。
# 注意上游 bug：test('test-signal-group', test_binding_group) 注册的是
# test-binding-group 二进制（test-signal-group 可执行文件从未被套件运行）。
UPSTREAM_TESTS = [
    ("test-application", "test-application"),
    ("test-menu-manager2", "test-menu-manager2"),
    ("test-state-machine", "test-state-machine"),
    ("test-binding-group", "test-binding-group"),
    ("test-signal-group", "test-binding-group"),  # 上游注册即用该二进制
    ("test-task-cache", "test-task-cache"),
    ("test-heap", "test-heap"),
    ("test-suggestion-buffer", "test-suggestion-buffer"),
    ("test-fuzzy-index", "test-fuzzy-index"),
    ("test-shortcut-chord", "test-shortcut-chord"),
    ("test-shortcut-overlays", "test-shortcut-overlays"),
    ("test-shortcut-theme", "test-shortcut-theme"),
    ("test-trie", "test-trie"),
    ("test-levenshtein", "test-levenshtein"),
    ("test-int-pair", "test-int-pair"),
    ("test-ring", "test-ring"),
    ("test-list-store", "test-list-store"),
    ("test-directory-reaper", "test-directory-reaper"),
    ("test-list-store-adapter", "test-list-store-adapter"),
    ("test-util", "test-util"),
    ("test-pattern-spec", "test-pattern-spec"),
    ("test-recursive-monitor", "test-recursive-monitor"),
    ("test-file-transfer", "test-file-transfer"),
    ("test-cancellable", "test-cancellable"),
    ("test-graph-model", "test-graph-model"),
    ("test-read-only-list-model", "test-read-only-list-model"),
    ("test-model-filter", "test-model-filter"),
    ("test-fuzzy-highlight", "test-fuzzy-highlight"),
    ("test-mutable-scoring", "test-mutable-scoring"),
]


class LibdazzleConan(ConanFile):
    name = "libdazzle"
    version = "3.44.0"
    description = "GNOME libdazzle — companion library for GTK3 applications (panels, widgets, fuzzy search, shortcuts)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libdazzle"
    url = "https://gitlab.gnome.org/GNOME/libdazzle"
    topics = ("gtk3", "widgets", "gnome")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    # Conan export_sources 机制：把 conandata.yml 声明的 patches/ 一并导出，
    # apply_conandata_patches() 在 build()/source() 里回放（G1 字面要求）。
    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # gtk/3.24.43 的 recipe pin glib/2.84.0.1（pango/atk/cairo-gobject 同图），
        # 顶层必须对齐同一版本避免图内版本冲突（R36）。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # OHOS profile 的 [buildenv] 前置 meson 包装器损坏
        # （ModuleNotFoundError: mesonbuild），走 ohpcd 预发布版本遮罩它
        # （playerctl 2.4.1.1 实证）。
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tools_folder = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(tools_folder)
        self._materialize_dep_libs()
        self._absolutize_pc_libs()
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "default_library": "shared" if self.options.shared else "static",
            "with_introspection": "false",   # g-ir-scanner 不可用
            "with_vapi": "false",            # valac 不可用
            "enable_gtk_doc": "false",
            "enable_tools": "false",         # 纯库包，不混装 dazzle-list-counters CLI
            "enable_tests": "true",          # 上游套件在 build() 真实执行
        })
        tc.generate()
        self._inject_meson_tools(tools_folder)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            # ninja 断点续跑：HMDFS 执行权限整窗抖动时（少量 custom_target
            # EACCES）重试即可续编；真编译错误在 3 次后照常失败。
            last = None
            for attempt in range(4):
                try:
                    self._materialize_dep_libs()
                    meson.build()
                    last = None
                    break
                except Exception as e:  # ConanException
                    last = e
                    self.output.warning(
                        f"meson.build attempt {attempt + 1}/4 failed ({e}); "
                        "retry after prewarm+45s (HMDFS file settle window)"
                    )
                    time.sleep(45)
            if last is not None:
                raise last
            self._run_upstream_tests()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        self._sanitize_pc_files()
        if self.settings.os == "OHOS":
            if self.options.shared:
                self._create_shared_lib_aliases(os.path.join(self.package_folder, "lib"))
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["dazzle-1.0"]
        incs = [
            d for d in ("include/libdazzle-1.0", "include")
            if os.path.isdir(os.path.join(self.package_folder, d))
        ]
        self.cpp_info.includedirs = incs or ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libdazzle-1.0")
        self.cpp_info.set_property("cmake_target_name", "libdazzle-1.0::libdazzle-1.0")
        self.cpp_info.set_property("pkg_config_name", "libdazzle-1.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # 不声明 cpp_info.requires：依赖链接顺序由依赖图及各包 .pc 的 Libs 承载
        # （gtk/3.24.43 同口径）。

    # ------------------------------------------------------------------
    # glib 构建工具注入（gtk/3.24.43 实证范式）
    # ------------------------------------------------------------------

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_glib_build_tools(self):
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        # 纯 python 工具：shell wrapper 调当前（签名）解释器执行，零链接、零 ELF，
        # 规避 HMDFS 对新解压脚本的 execve 信任延迟。
        for tool in ("glib-mkenums", "gdbus-codegen", "glib-genmarshal"):
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"GLib build tool missing: {src}")
            self._build_python_tool_wrapper(tool, src)
            self._prewarm_tool(os.path.join(tools_folder, tool))
        # ELF 工具：复制进构建目录（不污染 conan 缓存）并自签。
        for tool in ("glib-compile-resources", "glib-compile-schemas", "gobject-query"):
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"GLib build tool missing: {src}")
            dst = os.path.join(tools_folder, tool)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(dst)
            self._prewarm_tool(dst)
        return tools_folder

    def _prewarm_tool(self, path):
        # HMDFS 对新建文件的 execve 信任延迟整窗波动（同配置时好时坏，
        # augeas/libdazzle 实证）。在 generate() 阶段循环试跑 --help 直到
        # 进程能被 execve 为止（退出码不判定——ELF 工具在 generate() 阶段
        # 无 LD_LIBRARY_PATH 可能因缺库退出，但那已证明执行信任成立），
        # 确保 meson custom_target 不在中途撞 EACCES。
        deadline = time.time() + 240
        attempt = 0
        while True:
            attempt += 1
            try:
                subprocess.run(
                    [path, "--help"], stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=30,
                )
                # 能 execve 即信任已建立（rc 任意）
                if attempt > 1:
                    self.output.info(f"prewarm ok after {attempt} attempts: {os.path.basename(path)}")
                return
            except PermissionError:
                pass
            except subprocess.TimeoutExpired:
                return  # 能跑满 timeout 说明 execve 成功
            except Exception:
                pass
            if time.time() > deadline:
                raise RuntimeError(f"prewarm failed (trust window never opened): {path}")
            time.sleep(15)

    def _build_python_tool_wrapper(self, name, script):
        # 编译型启动器而非 #!/bin/sh 脚本：el2 HMDFS 上未签名文件的
        # execve 权限整窗抖动（同一文件几秒内时好时坏，libdazzle 3 次实证），
        # 而签名 ELF（binary-sign-tool selfSign）稳定可执行——与
        # glib-compile-resources 等复制后自签的 ELF 工具行为一致。
        #
        # 解释器选型（本宿主 execve 溯源策略实测）：
        #   - self-sign ELF → el1 bundle python：EACCES（应用签名卷，拒绝）
        #   - self-sign ELF → /storage 用户卷 python：OK（meson 同款解释器）
        # 故启动器固定用 /storage python，不能用 os.sys.executable
        # （conan 自身在 el1 python 下跑，由它编出的启动器 exec 它会被拒）。
        tools_folder = self._glib_tools_folder()
        launcher_c = os.path.join(tools_folder, "_launcher.c")
        python = None
        for cand in (
            "/storage/Users/currentUser/usr/local/bin/python3",
            shutil.which("python3"),
        ):
            if cand and os.path.isfile(cand):
                python = cand
                break
        if not python:
            raise FileNotFoundError("no usable python interpreter for launchers")
        if not os.path.isfile(launcher_c):
            with open(launcher_c, "w", encoding="utf-8", newline="\n") as h:
                h.write(
                    "#include <unistd.h>\n"
                    "#ifndef LAUNCH_PYTHON\n#error LAUNCH_PYTHON required\n#endif\n"
                    "#ifndef LAUNCH_SCRIPT\n#error LAUNCH_SCRIPT required\n#endif\n"
                    "int main(int argc, char *argv[]) {\n"
                    "    char *args[argc + 2];\n"
                    "    int i;\n"
                    "    args[0] = LAUNCH_PYTHON;\n"
                    "    args[1] = LAUNCH_SCRIPT;\n"
                    "    for (i = 1; i < argc; i++) args[i + 1] = argv[i];\n"
                    "    args[argc + 1] = (char *)0;\n"
                    "    execv(LAUNCH_PYTHON, args);\n"
                    "    return 127;\n"
                    "}\n"
                )
        wrapper = os.path.join(tools_folder, name)
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        # -D 宏需要内层双引号构成 C 字符串字面量
        py_def = '"%s"' % python.replace('\\', '\\\\').replace('"', '\\"')
        sc_def = '"%s"' % script.replace('\\', '\\\\').replace('"', '\\"')
        cmd = "{cc} -O2 -o {out} {src} -DLAUNCH_PYTHON={py} -DLAUNCH_SCRIPT={sc}".format(
            cc=cc, out=shlex.quote(wrapper), src=shlex.quote(launcher_c),
            py=shlex.quote(py_def), sc=shlex.quote(sc_def),
        )
        self.run(cmd)
        if not os.path.isfile(wrapper):
            raise RuntimeError(f"launcher compile failed: {wrapper}")
        os.chmod(wrapper, 0o755)
        if self.settings.os == "OHOS":
            self._sign_elf(wrapper)

    def _augment_glib_pkg_config(self, tools_folder):
        # meson gnome 模块经 pkg-config 变量定位 glib 工具：
        #   glib-2.0.pc: glib_mkenums（gnome.mkenums 需要）
        #   gio-2.0.pc:  glib_compile_resources（gnome.compile_resources 需要）
        # PkgConfigDeps 生成的 .pc 缺这些变量，缺任一都会
        # 'Could not get pkg-config variable' 配置失败。
        marker = "\nName:"
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            raise FileNotFoundError("PkgConfigDeps output missing: glib-2.0.pc")
        content = open(pc, encoding="utf-8").read()
        # OHOS musl 无 gettext：gi18n-lib.h 消费者引用 g_libintl_*，
        # 解析到 glib 包自带 libintl（gtk/3.24.43 同款处理）。
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Libs:") and "-lintl" not in line.split():
                line = line.rstrip("\r\n") + " -lintl\n"
            lines.append(line)
        content = "".join(lines)
        variables = {
            "glib_genmarshal": os.path.join(tools_folder, "glib-genmarshal"),
            "gobject_query": os.path.join(tools_folder, "gobject-query"),
            "glib_mkenums": os.path.join(tools_folder, "glib-mkenums"),
        }
        block = "".join(f"{k}={v.replace(os.sep, '/')}\n" for k, v in variables.items())
        if marker not in content:
            raise ValueError("Invalid glib-2.0.pc")
        content = content.replace(marker, f"\n{block}{marker}", 1)
        open(pc, "w", encoding="utf-8", newline="\n").write(content)

        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if os.path.isfile(gio_pc):
            gcontent = open(gio_pc, encoding="utf-8").read()
            gio_vars = {
                "gdbus_codegen": os.path.join(tools_folder, "gdbus-codegen"),
                "glib_compile_schemas": os.path.join(tools_folder, "glib-compile-schemas"),
                "glib_compile_resources": os.path.join(tools_folder, "glib-compile-resources"),
            }
            gblock = "".join(
                f"{k}={v.replace(os.sep, '/')}\n"
                for k, v in gio_vars.items() if f"{k}=" not in gcontent
            )
            if gblock and marker in gcontent:
                gcontent = gcontent.replace(marker, f"\n{gblock}{marker}", 1)
                open(gio_pc, "w", encoding="utf-8", newline="\n").write(gcontent)

    def _inject_meson_tools(self, tools_folder):
        # conan 生成的 meson native/cross ini 补齐 [binaries]：
        # ar/ranlib（llvm-ar 不在裸名 PATH）、pkg-config、glib-compile-resources。
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        cdir = os.path.dirname(cc) if os.path.sep in cc else ""
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
            if not pkg_config and cdir:
                cand = os.path.join(cdir, "pkg-config")
                if os.path.isfile(cand):
                    pkg_config = cand
        for fn in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, fn)
            if not os.path.isfile(nf):
                continue
            content = open(nf, encoding="utf-8").read()
            if "[binaries]" not in content:
                continue
            binaries = []
            if ar and "\nar =" not in content:
                binaries.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                binaries.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                binaries.append(f"pkg-config = '{pkg_config}'")
            gcr = os.path.join(tools_folder, "glib-compile-resources")
            if os.path.isfile(gcr) and "\nglib-compile-resources =" not in content:
                binaries.append(f"glib-compile-resources = '{gcr}'")
            if not binaries:
                continue
            content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(binaries) + "\n", 1)
            open(nf, "w", encoding="utf-8", newline="\n").write(content)

    @staticmethod
    def _elf_complete(path):
        # ELF 截断探测：e_shoff + e_shnum*e_shentsize 必须落在文件内。
        # 背景：el2 HMDFS 对新下载文件有异步修复/替换期，期间可能读到
        # 16 字节截断残片（libdazzle 实证），lld/clang 随机 ENOENT。
        # 这里**全量读取**：HMDFS 的内容物化由读触发，整读一遍等于
        # 主动把文件压实到本地视图，同时校验 ELF 头与节表边界。
        try:
            size = os.path.getsize(path)
            if size < 64:
                return False
            with open(path, "rb") as h:
                data = h.read()
            if len(data) != size:
                return False
            if data[:4] != b"\x7fELF":
                return True  # 非 ELF（文本/静态 ar）按可读判定
            import struct
            e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
            e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
            if e_shoff == 0:
                return True
            return size >= e_shoff + e_shnum * max(e_shentsize, 1)
        except OSError:
            return False

    def _dep_libs_mirror(self):
        return os.path.join(self.build_folder, "deplibs")

    def _materialize_dep_libs(self):
        # 依赖库镜像：conan 解压产物（p/<pkg>/p/lib 下的 .so）在本宿主
        # HMDFS 上对 clang/lld 稳定 ENOENT（同一进程读 glib/gtk 正常、
        # 读 cairo/pixman 等 13 个包必失败；conan python 自身却可读，
        # 修复呈异步/读触发，多次重试无效）。实证：普通进程 shutil 写出
        # 的文件对一切进程可读（glib/gtk 经 cp -r 落地、.o/.so 产物均
        # 正常）→ 把全部依赖库复制进构建目录镜像，.pc 一并指向镜像，
        # 彻底绕开 conan 解压产物。
        mirror = self._dep_libs_mirror()
        os.makedirs(mirror, exist_ok=True)
        deadline = time.time() + 480
        pending = {}
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                folder = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                if not os.path.isdir(folder):
                    continue
                for entry in os.listdir(folder):
                    if entry.endswith((".so", ".a")) or ".so." in entry:
                        pending[entry] = os.path.join(folder, entry)
        while pending:
            for entry, src in list(pending.items()):
                dst = os.path.join(mirror, entry)
                try:
                    if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src) \
                            and self._elf_complete(dst):
                        pending.pop(entry)
                        continue
                    # 先整读源文件（触发 HMDFS 物化），再复制
                    with open(src, "rb") as h:
                        h.read()
                    try:
                        os.unlink(dst)
                    except OSError:
                        pass
                    shutil.copyfile(src, dst)
                    if os.path.getsize(dst) != os.path.getsize(src) or not self._elf_complete(dst):
                        continue  # 复制不完整，下轮重试
                    pending.pop(entry)
                except OSError:
                    continue
            if not pending:
                break
            if time.time() > deadline:
                raise RuntimeError(
                    "dependency lib mirror not settled: %s" % ", ".join(sorted(pending)))
            time.sleep(10)
        return mirror

    def _absolutize_pc_libs(self):
        # 把生成 .pc Libs 里能在依赖包 lib 目录解析的 -l<name> 改写为
        # 绝对路径 .so（优先解析到 _materialize_dep_libs 的镜像副本）；
        # 同时把 Libs 中指向 conan 解压产物的既有绝对路径改写到镜像。
        import re as _re
        mirror = self._dep_libs_mirror()
        search_dirs = [mirror]
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                folder = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                if os.path.isdir(folder) and folder not in search_dirs:
                    search_dirs.append(folder)

        def _resolve(name):
            for d in search_dirs:
                for ext in (".so", ".a"):
                    cand = os.path.join(d, "lib%s%s" % (name, ext))
                    if os.path.isfile(cand):
                        return cand
            return None

        mirror_prefixes = [os.path.join(f, "") for f in search_dirs[1:]]
        for pc in glob.glob(os.path.join(self.generators_folder, "*.pc")):
            txt = open(pc, encoding="utf-8").read()
            changed = False
            out_lines = []
            for line in txt.splitlines(keepends=True):
                if line.startswith(("Libs:", "Libs.private:")):
                    head, sep, body = line.partition(":")
                    toks = body.split()
                    new_toks = []
                    for tok in toks:
                        if tok.startswith("/") and not tok.startswith(mirror):
                            for pref in mirror_prefixes:
                                if tok.startswith(pref):
                                    new_tok = os.path.join(mirror, os.path.basename(tok))
                                    if os.path.isfile(new_tok):
                                        tok = new_tok
                                        changed = True
                                    break
                        else:
                            m = _re.match(r"^-l(.+)$", tok)
                            if m:
                                path = _resolve(m.group(1))
                                if path:
                                    new_toks.append(path)
                                    changed = True
                                    continue
                        new_toks.append(tok)
                    line = head + sep + " " + " ".join(new_toks) + "\n"
                out_lines.append(line)
            if changed:
                open(pc, "w", encoding="utf-8", newline="\n").write("".join(out_lines))

    def _build_environment(self):
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        glib_folder = self.dependencies["glib"].package_folder
        env.prepend_path("PATH", os.path.join(glib_folder, "bin"))
        env.prepend_path("PATH", self._glib_tools_folder())
        # 镜像库目录优先：规避 conan 解压产物对 loader 的 ENOENT/EACCES
        env.prepend_path("LD_LIBRARY_PATH", self._dep_libs_mirror())
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        user_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
        if os.path.isdir(user_bin):
            env.prepend_path("PATH", user_bin)
        return env

    # ------------------------------------------------------------------
    # 上游测试：无显示环境经 broadway 后端真实执行（29 项注册套件）
    # ------------------------------------------------------------------

    def _run_upstream_tests(self):
        tests_dir = os.path.join(self.build_folder, "tests")
        if not os.path.isdir(tests_dir):
            self.output.warning("upstream tests dir missing, skip upstream suite")
            return
        results = []
        broadwayd = None
        display_ready = False
        gtk_bin = os.path.join(self.dependencies["gtk"].package_folder, "bin")
        bd = os.path.join(gtk_bin, "broadwayd")
        log_path = os.path.join(self.build_folder, "broadwayd.log")
        if os.path.isfile(bd):
            try:
                with open(log_path, "wb") as lf:
                    broadwayd = subprocess.Popen(
                        [bd, ":5"], stdout=lf, stderr=lf,
                        cwd=self.build_folder,
                    )
                time.sleep(2)
                if broadwayd.poll() is None:
                    display_ready = True
            except Exception as e:
                self.output.warning(f"broadwayd failed to start: {e}")
        else:
            self.output.warning(f"broadwayd not found at {bd}; GTK-init tests will fail")

        try:
            signed = set()
            for name, binary in UPSTREAM_TESTS:
                exe = os.path.join(tests_dir, binary)
                if not os.path.isfile(exe):
                    results.append((name, "MISSING"))
                    continue
                # 新编译的测试 ELF 在 el2 HMDFS 上执行权限整窗抖动 →
                # 执行前自签（签名 ELF 稳定可执行）。上游 bug：
                # test-signal-group 与 test-binding-group 注册同一二进制，
                # 按唯一路径去重，避免对已签文件二次签名报 FILE_NOT_FOUND。
                if self.settings.os == "OHOS" and exe not in signed:
                    self._sign_elf(exe)
                    signed.add(exe)
                env = dict(os.environ)
                env.setdefault("G_TEST_SRCDIR", tests_dir)
                env.setdefault("G_TEST_BUILDDIR", tests_dir)
                env.setdefault("GSETTINGS_BACKEND", "memory")
                env.setdefault("NO_AT_BRIDGE", "1")
                env.setdefault("G_DEBUG", "gc-friendly")
                if display_ready:
                    env["GDK_BACKEND"] = "broadway"
                    env["BROADWAY_DISPLAY"] = ":5"
                try:
                    p = subprocess.run(
                        [exe], cwd=tests_dir, env=env, timeout=120,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    )
                    results.append((name, "PASS" if p.returncode == 0 else f"FAIL({p.returncode})"))
                except subprocess.TimeoutExpired:
                    results.append((name, "TIMEOUT"))
        finally:
            if broadwayd is not None and broadwayd.poll() is None:
                broadwayd.terminate()
                try:
                    broadwayd.wait(timeout=5)
                except Exception:
                    broadwayd.kill()

        npass = sum(1 for _, r in results if r == "PASS")
        self.output.info("=" * 60)
        self.output.info(f"UPSTREAM TEST SUITE: {npass}/{len(results)} PASS "
                         f"(broadway display: {'available' if display_ready else 'UNAVAILABLE'})")
        for name, r in results:
            self.output.info(f"  {r:<12} {name}")
        self.output.info("=" * 60)
        with open(os.path.join(self.build_folder, "upstream-test-results.txt"), "w") as f:
            f.write(f"broadway_display={'yes' if display_ready else 'no'}\n")
            for name, r in results:
                f.write(f"{r}\t{name}\n")

    # ------------------------------------------------------------------
    # 打包收尾（gtk/3.24.43 实证范式）
    # ------------------------------------------------------------------

    def _sanitize_pc_files(self):
        import re
        pkg_inc = os.path.join(self.package_folder, "include")
        for pc in glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")):
            txt = open(pc, encoding="utf-8").read()
            txt = re.sub(r"^prefix=.*", f"prefix={self.package_folder}", txt, flags=re.M)
            lines = []
            for ln in txt.splitlines(True):
                if ln.startswith(("Cflags:", "Cflags.private:")):
                    head, sep, body = ln.partition(":")
                    kept = []
                    for tok in body.split():
                        m = re.match(r'^-I"?([^"]+)"?$', tok)
                        if not m:
                            kept.append(tok)
                            continue
                        p = m.group(1)
                        for var, val in (
                            ("${prefix}", self.package_folder),
                            ("${includedir}", pkg_inc),
                            ("${exec_prefix}", self.package_folder),
                            ("${datarootdir}", os.path.join(self.package_folder, "share")),
                            ("${datadir}", os.path.join(self.package_folder, "share")),
                            ("${libdir}", os.path.join(self.package_folder, "lib")),
                        ):
                            p = p.replace(var, val)
                        if os.path.isdir(p):
                            kept.append(tok)
                        else:
                            self.output.info(f"{os.path.basename(pc)}: drop non-existent -I {tok}")
                    ln = head + sep + " " + " ".join(kept) + "\n"
                lines.append(ln)
            txt = "".join(lines)
            open(pc, "w", encoding="utf-8", newline="\n").write(txt)

    def _create_shared_lib_aliases(self, libdir):
        # HMDFS 对 .so 符号链接链的 loader 解析不稳定（清单 #29/#36）：
        # 用实体复制替代 symlink（meson install 默认产 symlink）。本宿主
        # 上 meson 的 symlink 落地失败后只剩 libdazzle-1.0.so.0 实体文件，
        # 因此从任意真实 .so.* 文件（深版本优先）补齐全部别名。
        pattern = "libdazzle-1.0.so.*"
        aliases = ["libdazzle-1.0.so.0", "libdazzle-1.0.so"]
        candidates = [
            p for p in glob.glob(os.path.join(libdir, pattern))
            if os.path.isfile(p) and not os.path.islink(p)
            and not p.endswith(".so")
        ]
        if not candidates:
            return
        src = max(candidates, key=lambda p: (os.path.basename(p).count("."), os.path.getsize(p)))
        for name in aliases:
            alias = os.path.join(libdir, name)
            if os.path.lexists(alias) and os.path.isfile(alias) and not os.path.islink(alias):
                continue  # 已有实体文件（可能就是源本身）
            if os.path.lexists(alias):
                os.unlink(alias)
            shutil.copyfile(src, alias)

    def _sign_installed_elfs(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        candidates = [shutil.which("llvm-objcopy")]
        if cc and os.path.sep in cc:
            candidates.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates if p and os.path.isfile(p)), None)
        patterns = [
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ]
        cands = []
        for pat in patterns:
            cands.extend(glob.glob(pat, recursive=True))
        for binary in sorted(set(cands)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            if objcopy:
                self.run(f"{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(binary)} 2>/dev/null || true")
            self._sign_elf(binary)

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS signer missing: {signer}")
        self.run(shlex.join([signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"]))
