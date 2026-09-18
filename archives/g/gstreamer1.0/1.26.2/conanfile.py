#!/usr/bin/env python3
"""Conan recipe -- gstreamer1.0 1.26.2 (Meson).

GStreamer is a pipeline-based multimedia framework. This recipe builds the
core gstreamer library and plugins (coreelements, coretracers) for
OpenHarmony PC (aarch64).

Adaptation notes:
- Patch 0001 fixes Python script execution on HMDFS (glib-mkenums, etc.)
- NLS disabled (no gettext on OHOS); _() macro stubbed via c_args
- gst_parse disabled to avoid bison/flex dependency
- All introspection, tests, examples, docs, benchmarks disabled
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class Gstreamer1Conan(ConanFile):
    name = "gstreamer1.0"
    version = "1.26.2"
    description = "Open source multimedia framework"
    license = "LGPL"
    homepage = "https://gstreamer.freedesktop.org/"
    url = ""  # CI fills this

    package_type = "library"

    generators = ("PkgConfigDeps",)

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib2/2.88.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["nls"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["benchmarks"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["libunwind"] = "disabled"
        tc.project_options["libdw"] = "disabled"
        tc.project_options["bash-completion"] = "disabled"
        tc.project_options["ptp-helper"] = "disabled"
        tc.project_options["gst_parse"] = "false"
        tc.c_args.append("-Wno-error=implicit-function-declaration")
        tc.c_args.append("-Wno-error=int-conversion")
        tc.c_args.append("-Wno-int-conversion")
        tc.c_args.append("-Wno-implicit-function-declaration")
        tc.c_args.append("-Dgettext(x)=(x)")
        tc.c_args.append("-Dngettext(s,p,n)=((n)==1?(s):(p))")
        tc.generate()

        glib2_pc = self._get_glib2_prefix()
        if glib2_pc:
            import pathlib
            gen_dir = pathlib.Path(self.generators_folder)
            self._create_glib_subpkg_pcs(gen_dir, glib2_pc)

    def _get_glib2_prefix(self):
        for dep in self.dependencies.values():
            if dep.ref.name == "glib2":
                return str(dep.package_folder)
        return None

    def _create_glib_subpkg_pcs(self, gen_dir, prefix):
        libdir = f"{prefix}/lib"
        incdir = f"{prefix}/include/glib-2.0"
        incdir1 = f"{prefix}/lib/glib-2.0/include"
        bindir = f"{prefix}/bin"
        datadir = f"{prefix}/share"

        glib_pc_content = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/glib-2.0
includedir1=${{prefix}}/lib/glib-2.0/include
bindir=${{prefix}}/bin
datadir=${{prefix}}/share

glib_genmarshal=${{bindir}}/glib-genmarshal
gobject_query=${{bindir}}/gobject-query
glib_mkenums=${{bindir}}/glib-mkenums
glib_valgrind_suppressions=${{datadir}}/glib-2.0/valgrind/glib.supp

Name: GLib
Description: C Utility Library
Version: 2.88.0
Libs: -L"${{libdir}}" -lglib-2.0 -lgobject-2.0 -lgio-2.0 -lgmodule-2.0 -lgthread-2.0 -lffi -lintl -lm -lpthread -ldl -lrt
Cflags: -I"${{includedir}}" -I"${{includedir1}}"
Requires: pcre2 zlib
"""
        (gen_dir / "glib-2.0.pc").write_text(glib_pc_content)

        subpkgs = {
            "gobject-2.0.pc": ("GObject", "gobject-2.0", ["glib-2.0"]),
            "gio-2.0.pc": ("GIO", "gio-2.0", ["gobject-2.0"]),
            "gmodule-2.0.pc": ("GModule", "gmodule-2.0", ["glib-2.0"]),
            "gmodule-no-export-2.0.pc": ("GModule-no-export", "gmodule-2.0", ["glib-2.0"]),
            "gthread-2.0.pc": ("GThread", "gthread-2.0", ["glib-2.0"]),
            "gio-unix-2.0.pc": ("GIO-unix", None, ["gio-2.0"]),
        }
        for fname, (name, lib, requires) in subpkgs.items():
            req_str = ", ".join(requires)
            libs_line = f'Libs: -L"${{libdir}}" -l{lib}' if lib else ""
            pc = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/glib-2.0
includedir1=${{prefix}}/lib/glib-2.0/include

Name: {name}
Description: GLib sub-package ({name})
Version: 2.88.0
Requires: {req_str}
{libs_line}
Cflags: -I"${{includedir}}" -I"${{includedir1}}"
"""
            (gen_dir / fname).write_text(pc)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Run upstream meson test suite (equivalent to make check)
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = [
            "gstreamer-1.0",
            "gstbase-1.0",
            "gstcontroller-1.0",
            "gstnet-1.0",
            "gstcheck-1.0",
        ]
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]
        self.cpp_info.requires = ["glib2::glib2"]
