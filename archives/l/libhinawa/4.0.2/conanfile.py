#!/usr/bin/env python3
"""Conan recipe — libhinawa 4.0.2 (Meson)."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.28"


class LibhinawaConan(ConanFile):
    name = "libhinawa"
    version = "4.0.2"
    description = "GObject library for IEEE 1394 asynchronous communication"
    license = "LGPL-2.1-or-later"
    homepage = "https://git.kernel.org/pub/scm/libs/ieee1394/libhinawa.git/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib2/2.88.0", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        for variable in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(variable, None)

        tools = {
            name: shutil.which(name)
            for name in ("ar", "as", "strip", "nm", "ranlib", "pkg-config")
        }
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                "Required build tools not found in PATH: {}".format(", ".join(missing))
            )

        toolchain = MesonToolchain(self)
        toolchain.ar = tools["ar"]
        toolchain.as_ = tools["as"]
        toolchain.strip = tools["strip"]
        toolchain.binaries["nm"] = tools["nm"]
        toolchain.binaries["ranlib"] = tools["ranlib"]
        toolchain.binaries["pkg-config"] = tools["pkg-config"]
        toolchain.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        toolchain.project_options["doc"] = "false"
        toolchain.project_options["introspection"] = "false"
        toolchain.project_options["wrap_mode"] = "nofallback"
        toolchain.generate()

        self._write_glib_pkg_config_compatibility()

    def _write_glib_pkg_config_compatibility(self):
        glib = self.dependencies["glib2"].package_folder
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")

        if cross_building(self):
            helpers = {
                name: shutil.which(name)
                for name in ("glib-genmarshal", "glib-mkenums")
            }
        else:
            helpers = {
                name: os.path.join(glib, "bin", name)
                for name in ("glib-genmarshal", "glib-mkenums")
            }

        missing = [name for name, path in helpers.items() if not path or not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "Required GLib build helpers not found: {}".format(", ".join(missing))
            )

        if os.path.isfile(glib_pc):
            with open(glib_pc, encoding="utf-8") as handle:
                content = handle.read()
            if "glib_genmarshal=" not in content:
                content += "\nglib_genmarshal={}\n".format(helpers["glib-genmarshal"])
            if "glib_mkenums=" not in content:
                content += "glib_mkenums={}\n".format(helpers["glib-mkenums"])
            with open(glib_pc, "w", encoding="utf-8") as handle:
                handle.write(content)

        for name, description in (
            ("gobject-2.0", "GLib Type, Object, Parameter and Signal Library"),
            ("gio-2.0", "GLib I/O library"),
            ("gmodule-2.0", "GLib dynamic module loader"),
        ):
            pc_file = os.path.join(self.generators_folder, "{}.pc".format(name))
            if os.path.isfile(pc_file):
                continue
            with open(pc_file, "w", encoding="utf-8") as handle:
                handle.write(
                    "prefix={glib}\n"
                    "libdir=${{prefix}}/lib\n"
                    "includedir=${{prefix}}/include\n"
                    "includedir1=${{prefix}}/lib/glib-2.0/include\n\n"
                    "Name: {name}\n"
                    "Description: {description}\n"
                    "Version: 2.88.0\n"
                    "Requires: glib-2.0\n"
                    "Libs: -L\"${{libdir}}\"\n"
                    "Cflags: -I\"${{includedir}}\" -I\"${{includedir}}/glib-2.0\" "
                    "-I\"${{includedir1}}\"\n".format(
                        glib=glib, name=name, description=description
                    )
                )

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if not cross_building(self):
            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["hinawa"]
        self.cpp_info.includedirs = ["include/hinawa"]
        self.cpp_info.requires = ["glib2::glib2"]
        self.cpp_info.set_property("pkg_config_name", "hinawa")
