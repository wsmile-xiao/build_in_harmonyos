#!/usr/bin/env python3
"""Conan recipe for glib 2.84.0 on HarmonyOS PC (arm64).

Build system: meson
R26: glib is a system same-name library → default_library=static
R27: Dependencies reference @ohpcd/stable
R28: test_package/ exists
R32: settings.os judgment uses in ("Linux", "OHOS")
E090: Meson host_system == 'linux' fix applied via patches (0001, 0003, 0004)
Netlink disabled for HarmonyOS via patch (0004)
getpass() declaration added via patch (0002)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    rmdir,
)
from conan.tools.meson import MesonToolchain
from conan.tools.gnu import PkgConfigDeps

_MUSL_LINK_ARGS = ["-L/lib", "-l:ld-musl-aarch64.so.1"]


class GlibConan(ConanFile):
    name = "glib"
    version = "2.84.0"
    description = "GNOME core C utility library (glib, gobject, gio, gmodule, gthread)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/glib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("glib/2.84.0 is only supported on OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libffi/3.4.4")
        self.requires("pcre2/10.40")
        # zlib is system pre-installed
        # gettext (intl) is provided by musl libc on OHOS

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # Populate gvdb subproject (empty in git archive tarball)
        # Declared in conandata.yml as "gvdb" source
        gvdb_data = self.conan_data.get("gvdb")
        if gvdb_data:
            gvdb_dir = os.path.join(self.source_folder, "subprojects", "gvdb")
            rmdir(self, gvdb_dir)
            os.makedirs(gvdb_dir, exist_ok=True)
            get(self, **gvdb_data, strip_root=True, destination=gvdb_dir)
            if not os.path.exists(os.path.join(gvdb_dir, "meson.build")):
                raise ConanInvalidConfiguration(
                    "gvdb source extraction did not produce meson.build"
                )
            self.output.info("gvdb subproject populated from conandata")

    def _create_proxy_libintl_subproject(self):
        # On OHOS, gettext functions are provided by system musl libc. This
        # subproject supplies the header and Meson dependency before setup.
        proxy_dir = os.path.join(self.source_folder, "subprojects", "proxy-libintl")
        if not os.path.exists(os.path.join(proxy_dir, "meson.build")):
            os.makedirs(proxy_dir, exist_ok=True)

            # meson.build: link against system musl libc for gettext functions
            # On OHOS, gettext is in system musl libc (ld-musl-aarch64.so.1)
            # but not in SDK's libc.so. Using -l: syntax (standard linker
            # mechanism) instead of absolute path.
            with open(os.path.join(proxy_dir, "meson.build"), 'w') as f:
                f.write(
                    "project('proxy-libintl', 'c', version: '1.0')\n"
                    "# On OHOS, gettext functions are in system musl libc.\n"
                    "# SDK's libc.so lacks gettext, system musl libc has it.\n"
                    "cc = meson.get_compiler('c')\n"
                    "intl_dep = declare_dependency(\n"
                    "  include_directories: include_directories('.'),\n"
                    f"  link_args: {_MUSL_LINK_ARGS!r},\n"
                    ")\n"
                )

            # libintl.h: minimal header for OHOS musl libc gettext API
            with open(os.path.join(proxy_dir, "libintl.h"), 'w') as f:
                f.write(
                    '#ifndef _LIBINTL_H\n'
                    '#define _LIBINTL_H\n'
                    '\n'
                    '#include <locale.h>\n'
                    '\n'
                    '#ifdef __cplusplus\n'
                    'extern "C" {\n'
                    '#endif\n'
                    '\n'
                    'extern char *gettext(const char *) __attribute__((__format_arg__(1)));\n'
                    'extern char *dgettext(const char *, const char *) __attribute__((__format_arg__(2)));\n'
                    'extern char *dcgettext(const char *, const char *, int) __attribute__((__format_arg__(2)));\n'
                    'extern char *ngettext(const char *, const char *, unsigned long);\n'
                    'extern char *dngettext(const char *, const char *, const char *, unsigned long);\n'
                    'extern char *dcngettext(const char *, const char *, const char *, unsigned long, int);\n'
                    'extern char *bind_textdomain_codeset(const char *, const char *);\n'
                    'extern char *bindtextdomain(const char *, const char *);\n'
                    'extern char *textdomain(const char *);\n'
                    '\n'
                    '#ifdef __cplusplus\n'
                    '}\n'
                    '#endif\n'
                    '\n'
                    '#endif\n'
                )
            self.output.info("proxy-libintl subproject created with libintl.h")

    def generate(self):
        tc = MesonToolchain(self)
        # R26: System same-name library must use static linking
        tc.project_options["default_library"] = "static"
        # Disable optional features not available on OHOS
        tc.project_options["selinux"] = "disabled"
        tc.project_options["libmount"] = "disabled"
        tc.project_options["netlink"] = "disabled"
        tc.project_options["sysprof"] = "disabled"
        tc.project_options["documentation"] = "false"
        tc.project_options["man-pages"] = "disabled"
        tc.project_options["tests"] = "false"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.pkg_config_path = self.generators_folder
        tc.generate()
        self._inject_meson_archive_tools()
        PkgConfigDeps(self).generate()

        pcre2_pc = os.path.join(self.generators_folder, "pcre2.pc")
        libpcre2_pc = os.path.join(self.generators_folder, "libpcre2-8.pc")
        if os.path.exists(pcre2_pc) and not os.path.exists(libpcre2_pc):
            with open(pcre2_pc, "r") as source_file:
                pcre2_contents = source_file.read()
            with open(libpcre2_pc, "w") as destination_file:
                destination_file.write(
                    pcre2_contents.replace("Name: pcre2", "Name: libpcre2-8")
                )

    def build(self):
        self._create_proxy_libintl_subproject()

        # Apply all patches declared in conandata.yml (R3)
        apply_conandata_patches(self)

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        self._run_meson(
            f'meson setup --native-file "{native_file}" '
            f'"{self.build_folder}" "{self.source_folder}" --prefix=/'
        )
        self._run_meson(f'meson compile -C "{self.build_folder}"')

    def _inject_meson_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or os.path.join(bindir, "llvm-ar")
        ranlib = executables.get("ranlib") or os.path.join(bindir, "llvm-ranlib")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not bindir or not os.path.isfile(ar) or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as native:
            content = native.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        tools = f"[binaries]\nar = '{ar}'\n"
        if os.path.isfile(ranlib):
            tools += f"ranlib = '{ranlib}'\n"
        with open(native_file, "w", encoding="utf-8") as native:
            native.write(content.replace("[binaries]\n", tools, 1))

    def package(self):
        self._run_meson(
            f'meson install -C "{self.build_folder}" --destdir "{self.package_folder}"'
        )

    def _run_meson(self, command):
        ninja = os.environ.get("NINJA")
        if not ninja or not os.path.isfile(ninja):
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = executables.get("c", "")
            candidate = os.path.join(os.path.dirname(compiler), "ninja")
            ninja = candidate if compiler and os.path.isfile(candidate) else None
        if not ninja:
            ninja = shutil.which("ninja")
        if not ninja:
            raise ConanInvalidConfiguration("A Ninja executable is required to build glib")
        ninja_dir = os.path.dirname(ninja)
        self.run(f'PATH="{ninja_dir}:$PATH" NINJA="{ninja}" {command}')

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "glib")
        self.cpp_info.set_property("pkg_config_name", "glib-2.0")

        # Main glib libraries
        self.cpp_info.libs = ["glib-2.0", "gobject-2.0", "gio-2.0",
                              "gmodule-2.0", "gthread-2.0"]

        # System dependencies:
        # - m, pthread, rt, dl: standard libc/runtime
        # - z: zlib (system pre-installed)
        # gettext functions are in system musl libc (ld-musl-aarch64.so.1)
        self.cpp_info.system_libs = ["m", "pthread", "rt", "dl", "z"]

        if str(self.settings.os) == "OHOS":
            # OHOS SDK's libc.so lacks gettext, but its musl loader exports it.
            self.cpp_info.sharedlinkflags = _MUSL_LINK_ARGS
            self.cpp_info.exelinkflags = _MUSL_LINK_ARGS

        # Include paths: standard + glibconfig.h location
        self.cpp_info.includedirs = ["include/glib-2.0", "lib/glib-2.0/include"]
