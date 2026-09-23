#!/usr/bin/env python3
"""Conan recipe — gtk-vnc 1.5.0 (Meson, GTK3 VNC client widget).

OHOS 适配要点：
  - 构建系统: meson (upstream meson.build)
  - 官方源: download.gnome.org（含 keycodemapdb subproject，wrap_mode=nodownload）
  - 依赖均已发布到 ohpcd 制品仓并验证含 OHOS 二进制
  - glib 构建工具按 gdk-pixbuf/gtk 模式处理（wrapper + pkg-config 注入）
  - 禁用 introspection/vala/gi-docs/pulseaudio/sasl（避免额外工具链依赖）
  - OHOS 下对 .so 签名
"""
import glob
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GtkvncConan(ConanFile):
    name = "gtk-vnc"
    version = "1.5.0"
    description = "gtk-vnc — a VNC client viewer widget for GTK (gvnc / gtk-vnc / gvncpulse)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gtk-vnc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Align with published ohpcd binaries: glib/gtk/gdk-pixbuf/cairo 均
        # 以 shared=True 发布，顶层声明覆盖下游包可能的 shared=False pin。
        # 个别下游（如 pango）对 glib 有 shared=False 约束，按顶层意图覆盖；
        # 覆盖失败仅记录，不阻断（部分包可能不声明 shared 选项）。
        for dep in ("glib", "gtk", "gdk-pixbuf", "cairo"):
            try:
                self.options[dep].shared = True
            except Exception as e:  # 选项不存在/不可覆盖时记录并继续
                self.output.info(f"skip force-shared for {dep}: {e}")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # Direct deps only (glib/gtk/gdk-pixbuf/cairo 下游依赖由各自配方承载)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6.1", transitive_headers=True, transitive_libs=True)
        self.requires("gnutls/3.8.10", transitive_headers=True, transitive_libs=True)
        self.requires("gmp/6.3.0", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # 官方源 download.gnome.org（含 keycodemapdb subproject）；CI 干净环境
        # 与本地均走 get()，配方完全可复现。若主源瞬时不可达，conandata 的
        # url 列表内嵌权威镜像（USTC/TUNA/NJU），由 CI 镜像 fallback 机制处理。
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tools_folder = self._prepare_glib_build_tools()
        self._create_python_wrapper(tools_folder)
        self._augment_glib_pkg_config(tools_folder)
        self._create_pod2man_stub(tools_folder)
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "default_library": "shared" if self.options.shared else "static",
            "introspection": "disabled",
            "with-vala": "disabled",
            "gi-docs": "disabled",
            "pulseaudio": "disabled",
            "sasl": "disabled",
            "valgrind": "false",
        })
        tc.generate()
        self._inject_meson_tools(tools_folder)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            meson.test()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        self._sanitize_pc_files()
        if self.settings.os == "OHOS":
            if self.options.shared:
                self._create_shared_lib_aliases(os.path.join(self.package_folder, "lib"))
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["gtk-vnc-2.0", "gvnc-1.0"]
        incs = [
            d
            for d in ("include", "include/gvnc-1.0", "include/gtk-vnc-2.0")
            if os.path.isdir(os.path.join(self.package_folder, d))
        ]
        self.cpp_info.includedirs = incs or ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "gtk-vnc")
        self.cpp_info.set_property("cmake_target_name", "gtk-vnc::gtk-vnc")
        self.cpp_info.set_property("pkg_config_name", "gtk-vnc-2.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ---------- 环境 / GLib 构建工具 / 签名 ----------

    def _build_environment(self):
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        # Python 3.12 移除 distutils，meson 的 import('python') 校验需要它。
        # setuptools 提供 distutils 兼容层，经 SETUPTOOLS_USE_DISTUTILS=local 启用。
        env.define("SETUPTOOLS_USE_DISTUTILS", "local")
        glib_folder = self.dependencies["glib"].package_folder
        env.prepend_path("PATH", os.path.join(glib_folder, "bin"))
        env.prepend_path("PATH", self._glib_tools_folder())
        # ⚠️ 禁止向 LD_LIBRARY_PATH 注入依赖 libdir：gettext/glib 制品仓自带的
        # OHOS libintl.so.8 缺 gettext 符号，python3.12 在注入路径下加载即崩溃
        # （meson 探测 python 报 exit 127 → 误报 "missing distutils"）。
        # configure/compile 阶段无需运行时库（链接走 -L/rpath）；测试阶段由
        # conan 自动生成的 conanrun 环境提供依赖 LD_LIBRARY_PATH。
        user_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
        if os.path.isdir(user_bin):
            env.prepend_path("PATH", user_bin)
        return env

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_glib_build_tools(self):
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        for tool in ("glib-genmarshal", "glib-mkenums", "gdbus-codegen"):
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"GLib build tool missing: {src}")
            self._build_python_tool_wrapper(tool, src)
        for tool in ("glib-compile-resources", "gobject-query", "glib-compile-schemas", "gio-querymodules"):
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"GLib build tool missing: {src}")
            dst = os.path.join(tools_folder, tool)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(dst)
        return tools_folder

    def _build_python_tool_wrapper(self, name, script):
        # 纯 shell 包装（零编译）：规避部分 CI worker 链接器差异。
        # env -u LD_LIBRARY_PATH：conan build env 注入的依赖 libdir 里，
        # OHOS 版 libintl.so.8 缺 gettext 符号，python3.12 直接加载即崩溃
        # （meson 探测 python 报 exit 127 / "missing distutils" 的根因）。
        # 这些 glib 工具是纯 Python 脚本，运行期不需要依赖共享库，清空即可。
        tools_folder = self._glib_tools_folder()
        wrapper = os.path.join(tools_folder, name)
        python = os.path.realpath(sys.executable)
        q = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
        with open(wrapper, "w", encoding="utf-8", newline="\n") as h:
            h.write("#!/bin/sh\nexec env -u LD_LIBRARY_PATH {} {} \"$@\"\n".format(q(python), q(script)))
        os.chmod(wrapper, 0o755)

    def _create_python_wrapper(self, tools_folder):
        # meson 的 import('python').find_installation('python3') 会解析 python3 并
        # 直接执行它做 introspection；若该 python 是 conan build env 下的
        # python3.12，会因 LD_LIBRARY_PATH 命中缺符号的 OHOS libintl.so.8 崩溃
        # （exit 127 → meson 误报 "missing distutils"）。提供一个自含修复的
        # python3 wrapper：清空 LD_LIBRARY_PATH（纯 Python 工具运行期不依赖
        # conan 共享库）+ 设 SETUPTOOLS_USE_DISTUTILS=local（Python 3.12 无
        # distutils，meson 校验需要它），再 exec 真实 python。wrapper 自身不依赖
        # 外层 env，无论 meson 以何种方式调起都能正常工作。
        wrapper = os.path.join(tools_folder, "python3")
        python = os.path.realpath(sys.executable)
        q = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
        with open(wrapper, "w", encoding="utf-8", newline="\n") as h:
            h.write(
                "#!/bin/sh\n"
                "export SETUPTOOLS_USE_DISTUTILS=local\n"
                "exec env -u LD_LIBRARY_PATH {} \"$@\"\n".format(q(python))
            )
        os.chmod(wrapper, 0o755)

    def _augment_glib_pkg_config(self, tools_folder):
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            raise FileNotFoundError("PkgConfigDeps output missing: glib-2.0.pc")
        content = open(pc, encoding="utf-8").read()
        # glib 需链接 libintl（否则 ld.lld 报 undefined symbol: g_libintl_bindtextdomain /
        # g_libintl_textdomain）；参考 gtk 配方的处理，给 Libs 行补 -lintl。
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
        block = "".join(f"{k}={v.replace(os.sep,'/')}\n" for k, v in variables.items())
        marker = "\nName:"
        if marker not in content:
            raise ValueError("Invalid glib-2.0.pc")
        content = content.replace(marker, f"\n{block}{marker}", 1)
        open(pc, "w", encoding="utf-8", newline="\n").write(content)
        # gio-2.0.pc: meson gnome 模块隐式查询的工具变量
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if os.path.isfile(gio_pc):
            gcontent = open(gio_pc, encoding="utf-8").read()
            gio_vars = {
                "gdbus_codegen": os.path.join(tools_folder, "gdbus-codegen"),
                "glib_compile_schemas": os.path.join(tools_folder, "glib-compile-schemas"),
                "glib_compile_resources": os.path.join(tools_folder, "glib-compile-resources"),
                "gio_querymodules": os.path.join(tools_folder, "gio-querymodules"),
            }
            gblock = "".join(f"{k}={v.replace(os.sep,'/')}\n" for k, v in gio_vars.items() if f"{k}=" not in gcontent)
            if gblock and marker in gcontent:
                gcontent = gcontent.replace(marker, f"\n{gblock}{marker}", 1)
                open(gio_pc, "w", encoding="utf-8", newline="\n").write(gcontent)

    def _create_pod2man_stub(self, tools_folder):
        # gtk-vnc meson.build 顶层无条件 find_program('pod2man')（默认 required），
        # 部分 CI worker 无 perl 环境。提供最小 stub：输出一个合法的 man 页到
        # 末参数（@OUTPUT@），保证配置/构建不因文档工具缺失失败。
        stub = os.path.join(tools_folder, "pod2man")
        with open(stub, "w", encoding="utf-8", newline="\n") as h:
            h.write(
                "#!/bin/sh\n"
                "out=\n"
                "for a in \"$@\"; do out=\"$a\"; done\n"
                "if [ -n \"$out\" ]; then\n"
                "  printf '.TH GVNCCAPTURE 1\\n.SH NAME\\ngvnccapture - VNC capture tool\\n' > \"$out\"\n"
                "fi\n"
                "exit 0\n"
            )
        os.chmod(stub, 0o755)

    def _inject_meson_tools(self, tools_folder):
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
                        p = p.replace("${prefix}", self.package_folder)
                        p = p.replace("${includedir}", pkg_inc)
                        p = p.replace("${exec_prefix}", self.package_folder)
                        p = p.replace("${datarootdir}", os.path.join(self.package_folder, "share"))
                        p = p.replace("${datadir}", os.path.join(self.package_folder, "share"))
                        p = p.replace("${libdir}", os.path.join(self.package_folder, "lib"))
                        if os.path.isdir(p):
                            kept.append(tok)
                        else:
                            self.output.info(f"{os.path.basename(pc)}: drop non-existent -I {tok}")
                    ln = head + sep + " " + " ".join(kept) + "\n"
                lines.append(ln)
            txt = "".join(lines)
            open(pc, "w", encoding="utf-8", newline="\n").write(txt)

    def _create_shared_lib_aliases(self, libdir):
        import glob as _glob
        for pattern, aliases in [
            ("libgtk-vnc-2.0.so.*.*.*", ["libgtk-vnc-2.0.so.0", "libgtk-vnc-2.0.so"]),
            ("libgvnc-1.0.so.*.*.*", ["libgvnc-1.0.so.0", "libgvnc-1.0.so"]),
        ]:
            versioned = sorted(
                p for p in _glob.glob(os.path.join(libdir, pattern)) if os.path.isfile(p) and not os.path.islink(p)
            )
            if versioned:
                src = versioned[-1]
                for name in aliases:
                    alias = os.path.join(libdir, name)
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
                # 剥离旧 .codesign 段：该段可能不存在（首次签名），失败属预期，
                # 忽略并继续执行签名流程。
                self.run(f"{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(binary)} 2>/dev/null || true")
            self._sign_elf(binary)

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS signer missing: {signer}")
        self.run(shlex.join([signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"]))
