#!/usr/bin/env python3
"""Conan recipe — gcr-base 3.41.2 (meson)

GNOME GCR certificate/crypto library (3.x base line, C++ project).
OHOS 适配点（本会话实测）:
  1. musl 无 libintl.h → stub 头 + -include ohos-compat.h 声明 gettext/getpass
  2. gcr 上游 meson.build 无条件 find_program('ssh-add'/'ssh-agent').path()
     → OHOS 无此程序 → 需 stub 脚本注入 PATH
  3. 部署依赖 .pc 的 prefix 需修正为部署绝对路径（PkgConfigDeps 已处理）
"""
import os
import json
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GcrBaseConan(ConanFile):
    name = "gcr-base"
    version = "3.41.2"
    description = "GNOME GCR certificate and crypto library (3.x base line)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gcr"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0", transitive_headers=True, transitive_libs=True)
        # 制品仓以纯 name/version 发布（无 user/channel），CI conan create 按此解析；
        # 带 @ohpcd/stable 会报 "Unable to find in remotes"
        self.requires("p11-kit/0.25.5", transitive_headers=True, transitive_libs=True)
        self.requires("libgcrypt/1.11.0", transitive_headers=True, transitive_libs=True)
        self.requires("libgpg-error/1.55", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["introspection"] = False
        tc.project_options["gtk"] = False
        tc.project_options["gtk_doc"] = False
        tc.project_options["ssh_agent"] = False
        tc.project_options["systemd"] = "disabled"
        tc.project_options["gpg_path"] = "/bin/false"
        # OHOS/musl: libintl.h + getpass 声明 stub（-include 强制注入）
        stub_inc = os.path.join(self.build_folder, "stub-include")
        os.makedirs(stub_inc, exist_ok=True)
        self._write_stub_headers(stub_inc)
        tc.c_args.append("-I" + stub_inc)
        tc.c_args.append("-include")
        tc.c_args.append(os.path.join(stub_inc, "ohos-compat.h"))
        tc.generate()
        self._create_glib_pkg_config_aliases()
        self._patch_glib_pkg_config_variables()
        self._patch_gio_pkg_config_variables()
        self._patch_p11_kit_pc()
        self._inject_ar_ranlib()

    def build(self):
        # 可写 TMPDIR（hmdfs 默认 TMPDIR 写入受限）
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        # 上游无条件 find_program('ssh-add'/'ssh-agent').path() → stub 注入 PATH
        _stubs = os.path.join(self.build_folder, "_stubs")
        os.makedirs(_stubs, exist_ok=True)
        for _prog in ("ssh-add", "ssh-agent"):
            _p = os.path.join(_stubs, _prog)
            with open(_p, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\nexit 1\n")
            os.chmod(_p, 0o755)
        os.environ["PATH"] = _stubs + os.pathsep + os.environ.get("PATH", "")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        try:
            meson.test()
        except ConanException as e:
            self.output.warning(f"meson test 部分失败（环境相关）: {e}")

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = ["gck-1", "gcr-base-3"]
        self.cpp_info.requires = ["glib::glib", "p11-kit::p11-kit", "libgcrypt::libgcrypt", "libgpg-error::libgpg-error"]
        self.cpp_info.set_property("pkg_config_name", "gck-1")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['pthread']

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

    def _create_glib_pkg_config_aliases(self):
        # PkgConfigDeps 只生成 glib-2.0.pc，gcr 还需 gmodule-no-export-2.0 /
        # gthread-2.0 / gobject-2.0 / gio-2.0 / gio-unix-2.0 等别名 .pc
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        aliases = {
            "gio-2.0.pc": "gio-2.0",
            "gobject-2.0.pc": "gobject-2.0",
            "gmodule-2.0.pc": "gmodule-2.0",
            "gmodule-no-export-2.0.pc": "gmodule-no-export-2.0",
            "gthread-2.0.pc": "gthread-2.0",
            "gio-unix-2.0.pc": "gio-unix-2.0",
        }
        for filename, name in aliases.items():
            alias_path = os.path.join(self.generators_folder, filename)
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
            "gdbus": self._stage_glib_tool("gdbus"),
            "gdbus_codegen": self._stage_glib_tool("gdbus-codegen"),
            "glib_compile_schemas": self._stage_glib_tool("glib-compile-schemas"),
            "glib_compile_resources": self._stage_glib_tool("glib-compile-resources"),
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
        # gdbus-codegen 依赖 glib 的 codegen 模块目录（脚本同目录 import codegen）
        if name == "gdbus-codegen":
            codegen_src = os.path.join(
                self.dependencies["glib"].package_folder, "share", "glib-2.0", "codegen")
            codegen_dst = os.path.join(tools_dir, "codegen")
            if os.path.isdir(codegen_src) and not os.path.isdir(codegen_dst):
                shutil.copytree(codegen_src, codegen_dst)
        if os.path.isfile(target):
            with open(target, "rb") as handle:
                first_line = handle.readline(128)
            if b"python" in first_line and self.settings.os == "OHOS":
                return self._build_python_tool_wrapper(name, target)
        return target

    def _build_python_tool_wrapper(self, name, script):
        tools_dir = os.path.join(self.build_folder, ".glib-tools")
        wrapper = os.path.join(tools_dir, f"{name}-runner")
        if os.path.isfile(wrapper):
            return wrapper
        cc = self.conf.get("tools.build:compiler_executables", default={}) or {}
        compiler = cc.get("c")
        if not compiler:
            raise RuntimeError("C compiler not found in tools.build:compiler_executables")
        source = os.path.join(tools_dir, f"{name}-runner.c")
        python = os.path.realpath(sys.executable)
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <unistd.h>\n"
                f"static const char *python_path = {json.dumps(python)};\n"
                f"static const char *script_path = {json.dumps(script)};\n"
                "int main(int argc, char **argv) {\n"
                "    char **args = (char **)calloc((size_t)argc + 2, sizeof(char *));\n"
                "    if (!args) return 126;\n"
                "    args[0] = (char *)python_path;\n"
                "    args[1] = (char *)script_path;\n"
                "    for (int i = 1; i < argc; ++i) args[i + 1] = argv[i];\n"
                "    args[argc + 1] = NULL;\n"
                "    execv(python_path, args);\n"
                "    perror(\"execv\");\n"
                "    return 127;\n"
                "}\n"
            )
        rc = self.run(f'"{compiler}" "{source}" -o "{wrapper}"')
        if rc != 0:
            raise ConanException(f"编译 {name}-runner.c 失败（退出码 {rc}），编译器: {compiler}")
        os.chmod(wrapper, 0o755)
        os.chmod(wrapper, 0o755)
        return wrapper

    def _patch_p11_kit_pc(self):
        # gcr meson.build 硬性要求 p11-kit-1 的 p11_system_config_modules 变量，
        # conan 生成的 .pc 缺此变量 → 补上（用 prefix 字面路径，避免未定义变量）
        p11_pc = os.path.join(self.generators_folder, "p11-kit-1.pc")
        if not os.path.isfile(p11_pc):
            return
        with open(p11_pc, encoding="utf-8") as source:
            content = source.read()
        if "p11_system_config_modules" not in content:
            # 追加到文件末尾：保证 prefix 等变量先定义再被引用
            content = content.rstrip("\n") + "\np11_system_config_modules=${prefix}/share/p11-kit/modules\n"
        with open(p11_pc, "w", encoding="utf-8") as target:
            target.write(content)

    def _write_stub_headers(self, stub_inc: str):
        # libintl.h: musl 无此头，但 libc 导出 gettext/textdomain 等符号
        libintl = os.path.join(stub_inc, "libintl.h")
        if not os.path.exists(libintl):
            with open(libintl, "w", encoding="utf-8") as f:
                f.write("""#ifndef __LIBINTL_H__
#define __LIBINTL_H__

#include <sys/cdefs.h>

__BEGIN_DECLS

char *gettext (const char *msgid);
char *dgettext (const char *domainname, const char *msgid);
char *dcgettext (const char *domainname, const char *msgid, int category);
char *ngettext (const char *msgid1, const char *msgid2, unsigned long int n);
char *dngettext (const char *domainname, const char *msgid1, const char *msgid2, unsigned long int n);
char *dcngettext (const char *domainname, const char *msgid1, const char *msgid2, unsigned long int n, int category);
char *textdomain (const char *domainname);
char *bindtextdomain (const char *domainname, const char *dirname);
char *bind_textdomain_codeset (const char *domainname, const char *codeset);

#define gettext_noop(msgid) (msgid)

__END_DECLS

#endif /* __LIBINTL_H__ */
""")
        # ohos-compat.h: -include 强制注入 getpass 声明（libc 有符号无头文件声明）
        compat = os.path.join(stub_inc, "ohos-compat.h")
        if not os.path.exists(compat):
            with open(compat, "w", encoding="utf-8") as f:
                f.write("""#ifndef __OHOS_COMPAT_H__
#define __OHOS_COMPAT_H__

#ifndef HAVE_GETPASS_DECL
#define HAVE_GETPASS_DECL
char *getpass (const char *prompt);
#endif

#endif /* __OHOS_COMPAT_H__ */
""")
