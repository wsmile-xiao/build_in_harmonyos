#!/usr/bin/env python3
"""Conan recipe — gtk 3.24.43 (Meson, broadway backend).

OHOS 适配要点：
  - 构建系统: meson (upstream meson.build)
  - 后端: broadway HTML5 (禁用 X11/Wayland，适配鸿蒙无原生显示系统)
  - 依赖均已发布到 ohpcd 制品仓并验证含 OHOS 二进制
  - glib 构建工具按 gdk-pixbuf 模式处理（wrapper + pkg-config 注入）
  - OHOS 下对 .so 签名
"""
import glob
import json
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GtkConan(ConanFile):
    name = "gtk"
    version = "3.24.43"
    description = "GTK+ — multi-platform toolkit for creating graphical user interfaces (broadway backend for OHOS)"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gtk.org/"
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
        # Align with published ohpcd binaries (2026-08-22, 依赖项 PR #6117/6118/6120/6121 合并后):
        # 新版本依赖仅发布 shared=True binary（glib/2.84.0.1、atk/2.38.0.1.1、
        # cairo-gobject/1.18.4.2、gdk-pixbuf/2.44.6.1）；顶层声明覆盖 pango 对
        # glib 的 shared=False pin（R36，空缓存 graph 验证通过）。
        try:
            self.options["glib"].shared = True
            self.options["harfbuzz"].shared = True
            self.options["cairo"].shared = True
            self.options["pango"].shared = True
            self.options["gdk-pixbuf"].shared = True
            self.options["atk"].shared = True
            self.options["cairo-gobject"].shared = True
        except Exception:
            pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # Direct deps only; transitive (harfbuzz/pixman/freetype/fontconfig/libpng/zlib/expat)
        # are pulled via cairo/pango/gdk-pixbuf to avoid version conflicts (R36).
        # 2026-08-22: 依赖升级到已发布 OHOS binary 的版本（依赖项 PR #6118/6120/6121
        # 合并）；glib 保持 2.84.0.1（pango/atk/cairo-gobject/gdk-pixbuf 的 recipe
        # 均 pin 该版本，顶层声明 2.84.0.1.1 会触发版本冲突）。
        # pango 指向 1.50.14.1.1（依赖项 PR #6196）：旧 1.50.14 binary 绑定
        # glib 静态（制品仓缺 glib shared=False binary），新版本绑定 glib
        # shared=True 才能在图中直接复用（#29741/#29756 失败分析）。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("cairo-gobject/1.18.4.2", transitive_headers=True, transitive_libs=True)
        self.requires("pango/1.50.14.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6.1", transitive_headers=True, transitive_libs=True)
        self.requires("atk/2.38.0.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("fribidi/1.0.16", transitive_headers=True, transitive_libs=True)
        self.requires("libepoxy/1.5.10", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        staged = os.path.expanduser("~/tmp/builds/gtk-3.24.43.tar.xz")
        if os.path.isfile(staged):
            from conan.tools.files import check_sha256, unzip
            check_sha256(self, staged, sources["sha256"])
            unzip(self, staged, strip_root=True)
            return
        try:
            get(self, **sources, strip_root=True)
        except Exception as e:
            if not mirror_url:
                raise
            self.output.warning(f"Primary source failed ({e}), trying mirror")
            get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_fribidi_pc()
        tools_folder = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(tools_folder)
        self._create_pkg_config_alias("gmodule-2.0.pc", "gmodule-no-export-2.0.pc", "gmodule-no-export-2.0")
        self._sync_cairo_headers_from_gobject()
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "default_library": "shared" if self.options.shared else "static",
            "x11_backend": "false",
            "wayland_backend": "false",
            "broadway_backend": "true",
            "win32_backend": "false",
            "quartz_backend": "false",
            "xinerama": "no",
            "cloudproviders": "false",
            "profiler": "false",
            "tracker3": "false",
            "print_backends": "file",
            "colord": "no",
            "gtk_doc": "false",
            "man": "false",
            "introspection": "false",
            "demos": "false",
            "examples": "false",
            "tests": "false",
            "installed_tests": "false",
        })
        tc.generate()
        self._inject_meson_tools(tools_folder)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            self._strip_gresource_to_pixdata()
            meson.build()

    def _strip_gresource_to_pixdata(self):
        # 制品仓 gdk-pixbuf 不带构建期工具 gdk-pixbuf-pixdata，
        # 而 gen-gtk-gresources-xml.py 对全部 PNG 无条件写
        # preprocess="to-pixdata"，glib-compile-resources 编译期即失败。
        # configure 后剥掉该预处理属性：资源内嵌原始 PNG，运行时经
        # 标准 GdkPixbuf PNG loader 加载（GTK4 上游已移除 pixdata 机制）。
        xml_path = os.path.join(self.build_folder, "gtk", "gtk.gresources.xml")
        if not os.path.isfile(xml_path):
            self.output.warning(f"gresources xml missing: {xml_path}")
            return
        content = open(xml_path, encoding="utf-8").read()
        stripped = content.replace(" preprocess='to-pixdata'", "").replace(
            ' preprocess="to-pixdata"', ""
        )
        if stripped != content:
            open(xml_path, "w", encoding="utf-8", newline="\n").write(stripped)
            self.output.info("stripped to-pixdata preprocessing from gtk.gresources.xml")

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        self._sanitize_pc_files()
        if self.settings.os == "OHOS":
            if self.options.shared:
                self._create_shared_lib_aliases(os.path.join(self.package_folder, "lib"))
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["gtk-3", "gdk-3", "gailutil-3"]
        # 只保留包内真实存在的 include 子目录：meson 安装布局随选项变化，
        # 引用不存在的目录会让下游 CMakeDeps/PkgConfig 的 Imported target
        # 直接报 non-existent path（[54]）。
        incs = [
            d
            for d in ("include/gtk-3.0", "include/gdk-3.0", "include")
            if os.path.isdir(os.path.join(self.package_folder, d))
        ]
        self.cpp_info.includedirs = incs or ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "GTK")
        self.cpp_info.set_property("cmake_target_name", "GTK::GTK")
        self.cpp_info.set_property("pkg_config_name", "gtk+-3.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # 不声明 cpp_info.requires：直接依赖里 glib/pango 定义组件而
        # cairo/cairo-gobject/gdk-pixbuf/atk/fribidi/libepoxy 为无组件
        # 平铺包（[46][50][51] 三种引用写法均被 CMakeDeps 拒绝）。
        # 链接顺序与依赖由 graph 及各包 .pc 的 Libs 承载，无需此元数据。

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
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "gtk"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "gdk"))
        user_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
        if os.path.isdir(user_bin):
            env.prepend_path("PATH", user_bin)
        # 部分 CI worker 的 SDK lld 缺 libxml2.so.16（其 RUNPATH 只找
        # $ORIGIN/../lib），链接器探测（clang -Wl,--version）直接崩。
        # 把用户级 libxml2 拷入构建目录的隔离子目录并仅注入该目录，
        # 避免整目录注入遮蔽 sqlite3 等库；源缺失时目录为空、无害。
        fallback = os.path.join(self._glib_tools_folder(), "ld-fallback")
        os.makedirs(fallback, exist_ok=True)
        if not os.listdir(fallback):
            for pat in (
                os.path.join(os.path.expanduser("~"), "usr", "local", "lib", "libxml2.so.16*"),
                "/storage/Users/currentUser/usr/local/lib/libxml2.so.16*",
            ):
                for src_path in glob.glob(pat):
                    shutil.copy2(src_path, fallback)
        env.prepend_path("LD_LIBRARY_PATH", fallback)
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
        # 纯 shell 包装（零编译）：部分 CI worker 的 SDK lld 缺 libxml2.so.16，
        # 任何链接都会崩。wrapper 只需在 build machine 上以绝对路径调起
        # python 解释器执行脚本，无需生成 ELF，规避 worker 间链接器差异。
        tools_folder = self._glib_tools_folder()
        wrapper = os.path.join(tools_folder, name)
        python = os.path.realpath(sys.executable)
        q = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
        with open(wrapper, "w", encoding="utf-8", newline="\n") as h:
            h.write("#!/bin/sh\nexec {} {} \"$@\"\n".format(q(python), q(script)))
        os.chmod(wrapper, 0o755)

    def _augment_glib_pkg_config(self, tools_folder):
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            raise FileNotFoundError("PkgConfigDeps output missing: glib-2.0.pc")
        content = open(pc, encoding="utf-8").read()
        variables = {
            "glib_genmarshal": os.path.join(tools_folder, "glib-genmarshal"),
            "gobject_query": os.path.join(tools_folder, "gobject-query"),
            "glib_mkenums": os.path.join(tools_folder, "glib-mkenums"),
        }
        block = "".join(f"{k}={v.replace(os.sep,'/')}\n" for k,v in variables.items())
        lines=[]
        for line in content.splitlines(keepends=True):
            if line.startswith("Libs:") and "-lintl" not in line.split():
                line=line.rstrip("\r\n")+" -lintl\n"
            lines.append(line)
        content="".join(lines)
        marker="\nName:"
        if marker not in content:
            raise ValueError("Invalid glib-2.0.pc")
        content=content.replace(marker, f"\n{block}{marker}",1)
        open(pc,"w",encoding="utf-8",newline="\n").write(content)
        # gio-2.0.pc: meson gnome 模块隐式查询的工具变量 ——
        #   gdbus_codegen (gnome.gdbus_codegen)、glib_compile_schemas
        #   (gnome.compile_schemas)、glib_compile_resources
        #   (gnome.compile_resources)；PkgConfigDeps 生成的 .pc 均缺，
        #   缺任一都会 'Could not get pkg-config variable' 配置失败。
        gio_pc=os.path.join(self.generators_folder,"gio-2.0.pc")
        if os.path.isfile(gio_pc):
            gcontent=open(gio_pc,encoding="utf-8").read()
            gio_vars={
                "gdbus_codegen": os.path.join(tools_folder,"gdbus-codegen"),
                "glib_compile_schemas": os.path.join(tools_folder,"glib-compile-schemas"),
                "glib_compile_resources": os.path.join(tools_folder,"glib-compile-resources"),
                "gio_querymodules": os.path.join(tools_folder,"gio-querymodules"),
            }
            gblock="".join(f"{k}={v.replace(os.sep,'/')}\n" for k,v in gio_vars.items() if f"{k}=" not in gcontent)
            if gblock and marker in gcontent:
                gcontent=gcontent.replace(marker,f"\n{gblock}{marker}",1)
                open(gio_pc,"w",encoding="utf-8",newline="\n").write(gcontent)

    def _fix_fribidi_pc(self):
        # Upstream fribidi.pc uses -I${includedir}/fribidi; Conan PkgConfigDeps
        # often emits only -I${includedir}, so #include <fribidi.h> fails
        # (gdk/gdk.c:47). 同 pango 已验证修复。
        pc = os.path.join(self.generators_folder, "fribidi.pc")
        if not os.path.isfile(pc):
            return
        text = open(pc, encoding="utf-8").read()
        if "/fribidi" in text.split("Cflags:", 1)[-1]:
            return
        for old, new in (
            ('Cflags: -I"${includedir}"', 'Cflags: -I"${includedir}" -I"${includedir}/fribidi"'),
            ("Cflags: -I${includedir}", "Cflags: -I${includedir} -I${includedir}/fribidi"),
        ):
            if old in text:
                text = text.replace(old, new, 1)
                break
        open(pc, "w", encoding="utf-8", newline="\n").write(text)

    def _sync_cairo_headers_from_gobject(self):
        # 制品仓 cairo 与 cairo-gobject 为两个包，均携带 include/cairo/*.h；
        # 唯一实质差异是 cairo-features.h 的 CAIRO_HAS_GOBJECT_FUNCTIONS
        # （cairo 包未启用）。两份同名头同时在命令行上时，命中谁取决于
        # 聚合顺序（[23][25][26] 反复抖动翻车）。确定性修法：用 cairo-gobject
        # 包（启用 gobject 的完整构建，头集合为超集）的 include 树整体覆盖
        # 本地缓存中 cairo 包的头文件——磁盘上只剩一份头、与顺序无关；
        # .pc 的 libdir/Libs 一律不动，链接仍走原 cairo 包。CI 空缓存每次
        # 重新下载后由本方法重建，无跨构建残留。
        try:
            dep = self.dependencies["cairo-gobject"]
            cairo_dep = self.dependencies["cairo"]
        except KeyError:
            return
        norm = lambda s: s.replace(os.sep, "/")

        def first_inc(d):
            for x in d.cpp_info.includedirs:
                if not os.path.isabs(x):
                    x = os.path.join(d.package_folder, x)
                return norm(x)
            return None

        go_inc = first_inc(dep)
        cairo_inc = first_inc(cairo_dep)
        if not go_inc or not cairo_inc or go_inc == cairo_inc or not os.path.isdir(go_inc):
            return
        copied = 0
        for root, _dirs, files in os.walk(go_inc):
            rel = os.path.relpath(root, go_inc)
            dst_root = os.path.join(cairo_inc, rel) if rel != "." else cairo_inc
            os.makedirs(dst_root, exist_ok=True)
            for f in files:
                shutil.copy2(os.path.join(root, f), os.path.join(dst_root, f))
                copied += 1
        if copied:
            self.output.info(
                "synced %d cairo headers from cairo-gobject pkg over cairo pkg" % copied
            )

    def _create_pkg_config_alias(self, src_name, alias_name, pkg_name):
        src=os.path.join(self.generators_folder, src_name)
        alias=os.path.join(self.generators_folder, alias_name)
        if not os.path.isfile(src):
            raise FileNotFoundError(f"PkgConfigDeps missing: {src_name}")
        content=open(src,encoding="utf-8").read()
        lines=[]
        for line in content.splitlines(keepends=True):
            if line.startswith("Name:"):
                if pkg_name=="gmodule-no-export-2.0":
                    lines.append("gmodule_supported=true\n\n")
                lines.append(f"Name: {pkg_name}\n")
            else:
                lines.append(line)
        open(alias,"w",encoding="utf-8",newline="\n").write("".join(lines))

    def _inject_meson_tools(self, tools_folder):
        ce=self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc=ce.get("c") or ""
        cdir=os.path.dirname(cc) if os.path.sep in cc else ""
        ar=ce.get("ar")
        ranlib=ce.get("ranlib")
        if cdir:
            if not ar:
                cand=os.path.join(cdir,"llvm-ar")
                if os.path.isfile(cand): ar=cand
            if not ranlib:
                cand=os.path.join(cdir,"llvm-ranlib")
                if os.path.isfile(cand): ranlib=cand
        pkg_config=self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config=shutil.which("pkg-config") or shutil.which("pkgconf")
            if not pkg_config and cdir:
                cand=os.path.join(cdir,"pkg-config")
                if os.path.isfile(cand): pkg_config=cand
        for fn in ("conan_meson_native.ini","conan_meson_cross.ini"):
            nf=os.path.join(self.generators_folder, fn)
            if not os.path.isfile(nf): continue
            content=open(nf,encoding="utf-8").read()
            if "[binaries]" not in content: continue
            binaries=[]
            if ar and "\nar =" not in content: binaries.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content: binaries.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                binaries.append(f"pkg-config = '{pkg_config}'")
            gcr=os.path.join(tools_folder,"glib-compile-resources")
            if os.path.isfile(gcr) and "\nglib-compile-resources =" not in content:
                binaries.append(f"glib-compile-resources = '{gcr}'")
            if not binaries: continue
            content=content.replace("[binaries]\n","[binaries]\n"+"\n".join(binaries)+"\n",1)
            open(nf,"w",encoding="utf-8",newline="\n").write(content)

    def _sanitize_pc_files(self):
        import re
        pkg_inc = os.path.join(self.package_folder, "include")
        for pc in glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")):
            txt=open(pc,encoding="utf-8").read()
            txt=re.sub(r"^prefix=.*", f"prefix={self.package_folder}", txt, flags=re.M)
            # 剥掉指向包内不存在目录的 -I（如 include/gdk-3.0 随选项不安装），
            # 否则下游 PkgConfig Imported target 报 non-existent path（[54]）
            lines=[]
            for ln in txt.splitlines(True):
                if ln.startswith(("Cflags:", "Cflags.private:")):
                    head, sep, body = ln.partition(":")
                    kept=[]
                    for tok in body.split():
                        m=re.match(r'^-I"?([^"]+)"?$', tok)
                        if not m:
                            kept.append(tok); continue
                        p=m.group(1)
                        p=p.replace("${prefix}", self.package_folder)
                        p=p.replace("${includedir}", pkg_inc)
                        p=p.replace("${exec_prefix}", self.package_folder)
                        p=p.replace("${datarootdir}", os.path.join(self.package_folder,"share"))
                        p=p.replace("${datadir}", os.path.join(self.package_folder,"share"))
                        p=p.replace("${libdir}", os.path.join(self.package_folder,"lib"))
                        if os.path.isdir(p):
                            kept.append(tok)
                        else:
                            self.output.info(f"{os.path.basename(pc)}: drop non-existent -I {tok}")
                    ln=head+sep+" "+" ".join(kept)+"\n"
                lines.append(ln)
            txt="".join(lines)
            open(pc,"w",encoding="utf-8",newline="\n").write(txt)

    def _create_shared_lib_aliases(self, libdir):
        import glob as _glob
        for pattern, aliases in [
            ("libgtk-3.so.*.*.*", ["libgtk-3.so.0", "libgtk-3.so"]),
            ("libgdk-3.so.*.*.*", ["libgdk-3.so.0", "libgdk-3.so"]),
            ("libgailutil-3.so.*.*.*", ["libgailutil-3.so.0", "libgailutil-3.so"]),
        ]:
            versioned=sorted(p for p in _glob.glob(os.path.join(libdir,pattern)) if os.path.isfile(p) and not os.path.islink(p))
            if versioned:
                src=versioned[-1]
                for name in aliases:
                    alias=os.path.join(libdir,name)
                    if os.path.lexists(alias): os.unlink(alias)
                    shutil.copyfile(src,alias)

    def _sign_installed_elfs(self):
        signer="/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip signing"); return
        ce=self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc=ce.get("c") or ""
        candidates=[shutil.which("llvm-objcopy")]
        if cc and os.path.sep in cc:
            candidates.insert(0, os.path.join(os.path.dirname(cc),"llvm-objcopy"))
        objcopy=next((p for p in candidates if p and os.path.isfile(p)), None)
        patterns=[os.path.join(self.package_folder,"bin","*"), os.path.join(self.package_folder,"lib","**","*.so"), os.path.join(self.package_folder,"lib","**","*.so.*")]
        cands=[]
        for pat in patterns: cands.extend(glob.glob(pat, recursive=True))
        for binary in sorted(set(cands)):
            if not os.path.isfile(binary) or os.path.islink(binary): continue
            if objcopy:
                self.run(f"{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(binary)} 2>/dev/null || true")
            self._sign_elf(binary)

    def _sign_elf(self, binary):
        signer="/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS signer missing: {signer}")
        self.run(shlex.join([signer,"sign","-inFile",binary,"-outFile",binary,"-selfSign","1"]))

