#!/usr/bin/env python3
"""Conan recipe for jsonrpc-glib 3.44.0.

jsonrpc-glib is a JSON-RPC library for GLib, part of GNOME.
Build system: meson.  Dependencies: glib (gio, gobject), json-glib.
"""

import os
import re
import shutil
import configparser
from contextlib import contextmanager

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class JsonrpcGlibConan(ConanFile):
    name = "jsonrpc-glib"
    version = "3.44.0"
    description = "A JSON-RPC library for GLib"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/jsonrpc-glib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("json-glib/1.6.6")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmpdir()
        PkgConfigDeps(self).generate()
        self._create_glib_pkg_config_aliases()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["with_introspection"] = False
        tc.project_options["with_vapi"] = False
        tc.project_options["enable_gtk_doc"] = False
        tc.project_options["enable_tests"] = False
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_archive_tools()

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        meson = Meson(self)
        with self._host_tool_environment():
            meson.configure()
            meson.build()

    def package(self):
        Meson(self).install()
        if self.options.shared:
            libdir = os.path.join(self.package_folder, "lib")
            if os.path.isdir(libdir):
                candidates = [
                    name for name in os.listdir(libdir)
                    if name.startswith("libjsonrpc-glib-1.0.so.")
                ]
                if candidates:
                    source = os.path.join(libdir, sorted(candidates)[-1])
                    for name in ["libjsonrpc-glib-1.0.so", "libjsonrpc-glib-1.0.so.1"]:
                        unversioned = os.path.join(libdir, name)
                        if not os.path.exists(unversioned):
                            self.output.info(f"Creating {name} copy for OHOS loader")
                            shutil.copy2(source, unversioned)

    def package_info(self):
        self.cpp_info.libs = ["jsonrpc-glib-1.0"]
        self.cpp_info.includedirs = ["include/jsonrpc-glib-1.0", "include"]
        self.cpp_info.set_property("cmake_file_name", "jsonrpc-glib")
        self.cpp_info.set_property("cmake_target_name", "jsonrpc-glib::jsonrpc-glib")
        self.cpp_info.set_property("pkg_config_name", "jsonrpc-glib-1.0")

    # ── helper methods ──────────────────────────────────────────────

    def _create_glib_pkg_config_aliases(self):
        """Create gio-2.0.pc, gobject-2.0.pc etc. from glib-2.0.pc.

        The glib conan package (2.84.0) puts all libs in a single
        cpp_info with pkg_config_name='glib-2.0', so PkgConfigDeps
        generates only glib-2.0.pc.  Meson's dependency('gio-2.0')
        needs a separate gio-2.0.pc.  Also inject glib_genmarshal
        variable needed by gnome.genmarshal().
        """
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()

        # Inject glib_genmarshal variable if missing (needed by gnome.genmarshal)
        if "glib_genmarshal" not in content:
            prefix = ""
            for line in content.splitlines():
                if line.startswith("prefix="):
                    prefix = line.split("=", 1)[1].strip()
                    break
            if prefix:
                genmarshal = os.path.join(prefix, "bin", "glib-genmarshal")
                if os.path.isfile(genmarshal):
                    content = re.sub(
                        r"^Name:",
                        f"glib_genmarshal={genmarshal}\n\nName:",
                        content,
                        count=1,
                        flags=re.M,
                    )
                    with open(glib_pc, "w", encoding="utf-8") as target:
                        target.write(content)

        aliases = {
            "gio-2.0.pc": "gio-2.0",
            "gobject-2.0.pc": "gobject-2.0",
            "gmodule-2.0.pc": "gmodule-2.0",
            "gthread-2.0.pc": "gthread-2.0",
        }
        for filename, name in aliases.items():
            alias_path = os.path.join(self.generators_folder, filename)
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            with open(alias_path, "w", encoding="utf-8") as target:
                target.write(alias)

    def _inject_meson_archive_tools(self):
        """Inject ar/ranlib into meson native file (OHOS workaround).

        Meson auto-detects 'llvm-ar' but can't find it without the full
        path in the native file.  This mirrors the glib/json-glib pattern.
        """
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
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(native_file, encoding="utf-8")
        if not parser.has_section("binaries"):
            return
        if not parser.has_option("binaries", "ar"):
            parser.set("binaries", "ar", self._meson_string(ar))
        if os.path.isfile(ranlib) and not parser.has_option("binaries", "ranlib"):
            parser.set("binaries", "ranlib", self._meson_string(ranlib))
        with open(native_file, "w", encoding="utf-8") as native:
            parser.write(native, space_around_delimiters=True)

    def _ensure_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    @contextmanager
    def _host_tool_environment(self):
        """Clear LD_LIBRARY_PATH for OHOS to avoid conflicting system libs."""
        if str(self.settings.os) != "OHOS":
            yield
            return
        ld_library_path = os.environ.pop("LD_LIBRARY_PATH", None)
        try:
            yield
        finally:
            if ld_library_path is not None:
                os.environ["LD_LIBRARY_PATH"] = ld_library_path

    @staticmethod
    def _meson_string(value):
        return "'{}'".format(str(value).replace("\\", "/").replace("'", "\\'"))
