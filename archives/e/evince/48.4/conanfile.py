import glob
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class EvinceConan(ConanFile):
    name = "evince"
    version = "48.4"
    description = "GNOME document viewer (PDF/PostScript/DVI/comics...) for HarmonyOS PC"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/evince"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
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

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("libhandy/1.8.3", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6.1", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("poppler/25.12.0.2", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmpdir()
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        self._patch_glib_pkg_config_variables()
        self._create_glib_pkg_config_aliases()
        self._patch_gio_pkg_config_variables()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["viewer"] = "true"
        tc.project_options["previewer"] = "true"
        tc.project_options["thumbnailer"] = "true"
        tc.project_options["nautilus"] = "false"
        tc.project_options["comics"] = "disabled"
        tc.project_options["djvu"] = "disabled"
        tc.project_options["dvi"] = "disabled"
        tc.project_options["pdf"] = "enabled"
        tc.project_options["ps"] = "disabled"
        tc.project_options["tiff"] = "disabled"
        tc.project_options["xps"] = "disabled"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["user_doc"] = "false"
        tc.project_options["introspection"] = "false"
        tc.project_options["dbus"] = "false"
        tc.project_options["keyring"] = "disabled"
        tc.project_options["gtk_unix_print"] = "disabled"
        tc.project_options["thumbnail_cache"] = "disabled"
        tc.project_options["multimedia"] = "disabled"
        tc.project_options["gspell"] = "disabled"
        tc.project_options["systemduserunitdir"] = "no"
        tc.generate()
        self._inject_ar_ranlib()

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        if self.settings.os == "OHOS":
            self._sign_binaries()
            self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = ["evdocument3", "evview3"]
        self.cpp_info.requires = [
            "glib::gio-2.0",
            "glib::gobject-2.0",
            "glib::glib-2.0",
            "gtk::gtk",
            "libhandy::libhandy",
            "libxml2::libxml2",
            "gdk-pixbuf::gdk-pixbuf",
            "cairo::cairo",
            "poppler::poppler",
            "zlib::zlib",
        ]
        self.cpp_info.includedirs = ["include/evince/3.0", "include/evince/3.0/libdocument", "include/evince/3.0/libview", "include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "evince")
        self.cpp_info.set_property("cmake_target_name", "evince::evince")
        self.cpp_info.set_property("pkg_config_name", "evince-document-3.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    def _inject_ar_ranlib(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if not ar:
            cc = compiler_executables.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insertion = "[binaries]\nar = '{}'\n".format(ar)
                if ranlib:
                    insertion += "ranlib = '{}'\n".format(ranlib)
                content = content.replace("[binaries]\n", insertion, 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _ensure_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _augment_glib_pkg_config(self):
        # glib.so NEEDED libintl.so.8，PkgConfigDeps 生成的 Libs 缺 -lintl，
        # OHOS lld 用 --no-allow-shlib-undefined 严格校验，链接 libevdocument3
        # 时若缺 -lintl 会报 g_libintl_* 未定义（libayatana-indicator 同款先例）。
        for pc_name in ("glib-2.0.pc", "gio-2.0.pc", "gobject-2.0.pc",
                        "gmodule-2.0.pc", "gthread-2.0.pc"):
            pc = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc):
                continue
            lines = []
            for line in open(pc, encoding="utf-8").read().splitlines(keepends=True):
                if line.startswith("Libs:") and "-lintl" not in line.split():
                    line = line.rstrip("\r\n") + " -lintl\n"
                lines.append(line)
            open(pc, "w", encoding="utf-8", newline="\n").write("".join(lines))

    def _create_glib_pkg_config_aliases(self):
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        aliases = {
            "gio-2.0.pc": "gio-2.0",
            "gobject-2.0.pc": "gobject-2.0",
            "gmodule-2.0.pc": "gmodule-2.0",
            "gthread-2.0.pc": "gthread-2.0",
        }
        for filename, name in aliases.items():
            alias_path = os.path.join(self.generators_folder, filename)
            # PkgConfigDeps already emits the per-component .pc (with the
            # correct -lgobject-2.0 / -lgio-2.0 libs) when the glib recipe
            # declares components; only synthesize an alias when it is absent.
            if os.path.isfile(alias_path):
                continue
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            with open(alias_path, "w", encoding="utf-8") as target:
                target.write(alias)

    def _patch_glib_pkg_config_variables(self):
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        variables = {
            "glib_genmarshal": self._stage_glib_tool("glib-genmarshal"),
            "gobject_query": self._stage_glib_tool("gobject-query"),
            "glib_mkenums": self._stage_glib_tool("glib-mkenums"),
        }
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        for variable, value in variables.items():
            if re.search(rf"^{re.escape(variable)}=", content, flags=re.M):
                content = re.sub(
                    rf"^{re.escape(variable)}=.*$",
                    f"{variable}={value}",
                    content,
                    flags=re.M,
                )
            else:
                content = f"{variable}={value}\n" + content
        with open(glib_pc, "w", encoding="utf-8") as target:
            target.write(content)

    def _patch_gio_pkg_config_variables(self):
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if not os.path.isfile(gio_pc):
            return
        variables = {
            "gio": self._stage_glib_tool("gio"),
            "gio_querymodules": self._stage_glib_tool("gio-querymodules"),
            "glib_compile_schemas": self._stage_glib_tool("glib-compile-schemas"),
            "glib_compile_resources": self._stage_glib_tool("glib-compile-resources"),
            "gdbus": self._stage_glib_tool("gdbus"),
            "gdbus_codegen": self._stage_glib_tool("gdbus-codegen"),
            "gresource": self._stage_glib_tool("gresource"),
            "gsettings": self._stage_glib_tool("gsettings"),
        }
        with open(gio_pc, encoding="utf-8") as source:
            content = source.read()
        for variable, value in variables.items():
            if re.search(rf"^{re.escape(variable)}=", content, flags=re.M):
                content = re.sub(
                    rf"^{re.escape(variable)}=.*$",
                    f"{variable}={value}",
                    content,
                    flags=re.M,
                )
            else:
                content = f"{variable}={value}\n" + content
        with open(gio_pc, "w", encoding="utf-8") as target:
            target.write(content)

    def _stage_glib_tool(self, name):
        source = os.path.join(self.dependencies["glib"].package_folder, "bin", name)
        tools_dir = os.path.join(self.build_folder, ".glib-tools")
        os.makedirs(tools_dir, exist_ok=True)
        target = os.path.join(tools_dir, name)
        if os.path.isfile(source) and not os.path.isfile(target):
            shutil.copy2(source, target)
            os.chmod(target, 0o755)
        if os.path.isfile(target):
            with open(target, "rb") as handle:
                first_line = handle.readline(128)
            if b"python" in first_line and self.settings.os == "OHOS":
                # Python 脚本工具（glib-genmarshal/glib-mkenums 等）：用 sh
                # wrapper exec python 解释器，避免 clang 链接 C runner——
                # CI worker 沙箱中 lld 缺 libxml2.so.16 无法启动，且刚链接
                # 的 runner ELF 未签名无法 exec（E266 同类，仿
                # libayatana-indicator 0.9.5 先例）。
                return self._wrap_python_tool(name, source)
            if self.settings.os == "OHOS":
                self._make_elf_tool_runnable(target)
        return target

    def _wrap_python_tool(self, name, script):
        wrapper = os.path.join(self.build_folder, ".glib-tools", name)
        if os.path.isfile(wrapper):
            return wrapper
        python = os.path.realpath(sys.executable)
        q = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#!/bin/sh\nexec {} {} \"$@\"\n".format(q(python), q(script)))
        os.chmod(wrapper, 0o755)
        return wrapper

    def _make_elf_tool_runnable(self, tool):
        # OHOS 要求 ELF 带 .codesign 段才能 exec（未签名报 Operation not
        # permitted，astap 对 FPC 工具同样处理）；glib 包内工具未签名。
        # 顺序关键：先 patchelf 注入 runpath（指向 glib libdir 以加载
        # libgio-2.0.so.0 等），再签名——签名后再改 ELF 会破坏 .codesign，
        # exec 仍报 Operation not permitted。
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        glib_libdir = os.path.join(self.dependencies["glib"].package_folder, "lib")
        self.run('patchelf --set-rpath "{r}" "{f}"'.format(r=glib_libdir, f=tool))
        if os.path.isfile(objcopy) and os.path.isfile(signer):
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=tool
            ))
            signed = tool + ".signed"
            self.run('{sg} sign -inFile "{f}" -outFile "{o}" -selfSign 1'.format(
                sg=signer, f=tool, o=signed
            ))
            if os.path.isfile(signed):
                os.replace(signed, tool)
        os.chmod(tool, 0o755)

    @staticmethod
    def _unique(items):
        seen = set()
        result = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def _sign_binaries(self):
        bindir = os.path.join(self.package_folder, "bin")
        binaries = sorted(
            os.path.join(bindir, name)
            for name in os.listdir(bindir)
            if os.path.isfile(os.path.join(bindir, name))
        ) if os.path.isdir(bindir) else []
        if not binaries:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise FileNotFoundError(f"Required OHOS signing tool is missing: {tool}")
        for binary in binaries:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=binary
            ))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=binary
            ))

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_objects += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_objects:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise FileNotFoundError(f"Required OHOS signing tool is missing: {tool}")
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=shared_object
            ))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=shared_object
            ))
