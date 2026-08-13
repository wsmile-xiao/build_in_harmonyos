#!/usr/bin/env python3
"""Conan recipe for json-glib 1.6.6."""

import os
import re
import shutil
import configparser
from contextlib import contextmanager

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.build import can_run


class JsonGlibConan(ConanFile):
    name = "json-glib"
    version = "1.6.6"
    description = "JSON parser and generator library integrated with GLib"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/Projects/JsonGlib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_upstream_tests": False,
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
        self.requires("glib/2.84.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._generate_enum_sources()

    def generate(self):
        self._ensure_tmpdir()
        PkgConfigDeps(self).generate()
        self._create_glib_pkg_config_aliases()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["gtk_doc"] = "disabled"
        tc.project_options["man"] = False
        tc.project_options["tests"] = self.options.with_upstream_tests
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
        if self.options.with_upstream_tests and can_run(self):
            meson.test()

    def package(self):
        Meson(self).install()
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            candidates = [
                name for name in os.listdir(libdir)
                if name.startswith("libjson-glib-1.0.so.")
            ]
            if candidates:
                source = os.path.join(libdir, sorted(candidates)[-1])
                for name in ["libjson-glib-1.0.so", "libjson-glib-1.0.so.0"]:
                    unversioned = os.path.join(libdir, name)
                    if not os.path.exists(unversioned):
                        self.output.info(f"Creating {name} copy for OHOS loader")
                        shutil.copy2(source, unversioned)

    def package_info(self):
        self.cpp_info.libs = ["json-glib-1.0"]
        self.cpp_info.includedirs = ["include/json-glib-1.0", "include"]
        self.cpp_info.set_property("cmake_file_name", "json-glib")
        self.cpp_info.set_property("cmake_target_name", "json-glib::json-glib")
        self.cpp_info.set_property("pkg_config_name", "json-glib-1.0")

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
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(native_file, encoding="utf-8")
        if not parser.has_section("binaries") or parser.has_option("binaries", "ar"):
            return
        parser.set("binaries", "ar", self._meson_string(ar))
        if os.path.isfile(ranlib):
            parser.set("binaries", "ranlib", self._meson_string(ranlib))
        with open(native_file, "w", encoding="utf-8") as native:
            parser.write(native, space_around_delimiters=True)

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
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            with open(alias_path, "w", encoding="utf-8") as target:
                target.write(alias)

    def _ensure_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    @contextmanager
    def _host_tool_environment(self):
        if str(self.settings.os) != "OHOS":
            yield
            return
        ld_library_path = os.environ.pop("LD_LIBRARY_PATH", None)
        try:
            yield
        finally:
            if ld_library_path is not None:
                os.environ["LD_LIBRARY_PATH"] = ld_library_path

    def _meson_string(self, value):
        return "'{}'".format(str(value).replace("\\", "/").replace("'", "\\'"))

    def _generate_enum_sources(self):
        json_dir = os.path.join(self.source_folder, "json-glib")
        public_headers = [
            "json-builder.h",
            "json-generator.h",
            "json-gobject.h",
            "json-gvariant.h",
            "json-parser.h",
            "json-path.h",
            "json-reader.h",
            "json-types.h",
            "json-utils.h",
            "json-version-macros.h",
        ]
        enums = []
        for header in public_headers:
            path = os.path.join(json_dir, header)
            with open(path, encoding="utf-8") as source:
                content = source.read()
            for body, enum_name in re.findall(
                r"typedef\s+enum\s*\{(.*?)\}\s*(Json[A-Za-z0-9_]+)\s*;",
                content,
                flags=re.S,
            ):
                values = []
                for raw_line in body.splitlines():
                    line = raw_line.split("/*", 1)[0].strip().rstrip(",")
                    if not line or line.startswith("#"):
                        continue
                    value = line.split("=", 1)[0].strip()
                    if value:
                        values.append(value)
                if values:
                    enums.append((header, enum_name, values))

        if not enums:
            raise ConanInvalidConfiguration("No public Json enum declarations found")

        header_path = os.path.join(json_dir, "json-enum-types.h")
        source_path = os.path.join(json_dir, "json-enum-types.c")
        with open(header_path, "w", encoding="utf-8", newline="\n") as header_file:
            header_file.write(
                "#ifndef __JSON_ENUM_TYPES_H__\n"
                "#define __JSON_ENUM_TYPES_H__\n\n"
                "#if !defined(__JSON_GLIB_INSIDE__) && !defined(JSON_COMPILATION)\n"
                '#error "Only <json-glib/json-glib.h> can be included directly."\n'
                "#endif\n\n"
                "#include <glib-object.h>\n"
                "#include <json-glib/json-version-macros.h>\n\n"
                "G_BEGIN_DECLS\n\n"
            )
            for _, enum_name, _ in enums:
                func = self._enum_func(enum_name)
                short = self._enum_short(enum_name)
                header_file.write(
                    "JSON_AVAILABLE_IN_1_0\n"
                    f"GType {func} (void) G_GNUC_CONST;\n"
                    f"#define JSON_TYPE_{short} ({func}())\n\n"
                )
            header_file.write("G_END_DECLS\n\n#endif /* !__JSON_ENUM_TYPES_H__ */\n")

        with open(source_path, "w", encoding="utf-8", newline="\n") as source_file:
            source_file.write(
                "#ifndef JSON_COMPILATION\n"
                "#define JSON_COMPILATION\n"
                "#endif\n\n"
                '#include "config.h"\n'
                '#include "json-enum-types.h"\n'
            )
            for header, _, _ in enums:
                source_file.write(f'#include "{header}"\n')
            source_file.write("\n")
            for _, enum_name, values in enums:
                func = self._enum_func(enum_name)
                source_file.write(
                    "GType\n"
                    f"{func} (void)\n"
                    "{\n"
                    "  static gsize g_enum_type_id__volatile = 0;\n\n"
                    "  if (g_once_init_enter (&g_enum_type_id__volatile))\n"
                    "    {\n"
                    "      static const GEnumValue values[] = {\n"
                )
                for value in values:
                    source_file.write(
                        f'        {{ {value}, "{value}", "{self._value_nick(value)}" }},\n'
                    )
                source_file.write(
                    "        { 0, NULL, NULL }\n"
                    "      };\n\n"
                    "      GType g_enum_type_id =\n"
                    f'        g_enum_register_static (g_intern_static_string ("{enum_name}"), values);\n\n'
                    "      g_once_init_leave (&g_enum_type_id__volatile, g_enum_type_id);\n"
                    "    }\n\n"
                    "  return g_enum_type_id__volatile;\n"
                    "}\n\n"
                )

    @staticmethod
    def _enum_func(enum_name):
        snake = re.sub(r"(?<!^)([A-Z])", r"_\1", enum_name).lower()
        return f"{snake}_get_type"

    @staticmethod
    def _enum_short(enum_name):
        name = enum_name[4:] if enum_name.startswith("Json") else enum_name
        return re.sub(r"(?<!^)([A-Z])", r"_\1", name).upper()

    @staticmethod
    def _value_nick(value):
        nick = value
        if nick.startswith("JSON_"):
            nick = nick[5:]
        return nick.lower().replace("_", "-")
