#!/usr/bin/env python3
"""Conan recipe — gobject-introspection 1.78.1 (Meson).

GObject Introspection provides metadata about GObject libraries: .gir and
.typelib files, plus tools (g-ir-scanner, g-ir-compiler, g-ir-generate).
Adapted to HarmonyOS PC (aarch64). See notes.md for platform adaptations.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps


class GobjectIntrospectionConan(ConanFile):
    name = "gobject-introspection"
    version = "1.78.1"
    description = "GObject Introspection — metadata for GObject libraries"
    license = "LGPL-2.1+"
    homepage = "https://gi.readthedocs.io/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib2/2.88.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: static build — glib2 and its deps (zlib, pcre2, libffi) are
        # static without -fPIC; building shared would fail at link time.
        tc.project_options["default_library"] = "static"
        # Disable introspection data generation: the g-ir-scanner Python
        # script requires importing _giscanner.so, which cannot be dlopen'd
        # on HarmonyOS due to hmmac security labels (E212).
        tc.project_options["build_introspection_data"] = "false"
        # No cairo or doctool deps available on the target.
        tc.project_options["cairo"] = "disabled"
        tc.project_options["doctool"] = "disabled"
        tc.project_options["wrap_mode"] = "nofallback"
        tc.generate()

        # R33: The Conan profile's [buildenv] PATH includes /data/service/hnp/bin
        # (HarmonyOS platform-standard HNP toolchain directory, not a machine-
        # specific path). However, meson's subprocess may not inherit it.
        # Set AR explicitly so meson's archiver detection succeeds.
        # This is equivalent to the profile's [buildenv] PATH and uses the
        # same platform-standard directory.
        env = Environment()
        env.define("AR", "/data/service/hnp/bin/llvm-ar")
        env.prepend_path("PATH", "/data/service/hnp/bin")
        envvars = env.vars(self)
        envvars.save_script("conan_buildenv")

        # glib2 Conan package declares a single pkg_config_name "glib-2.0"
        # that bundles all libs. But gobject-introspection's meson.build looks
        # for separate gobject-2.0, gio-2.0, gmodule-2.0, gio-unix-2.0, and
        # libffi via pkg-config. Generate wrapper .pc files that alias
        # glib-2.0 so meson can find all components.
        gen_dir = self.generators_folder
        glib2_info = self.dependencies["glib2"]
        glib2_root = glib2_info.package_folder

        # The Conan-generated glib-2.0.pc already has correct paths.
        # Create wrappers for the other components meson needs.
        for pc_name, desc in [
            ("gobject-2.0", "GObject"),
            ("gio-2.0", "GIO"),
            ("gmodule-2.0", "GModule"),
            ("gio-unix-2.0", "GIO Unix"),
            ("libffi", "libffi"),
        ]:
            pc_path = os.path.join(gen_dir, f"{pc_name}.pc")
            if not os.path.exists(pc_path):
                with open(pc_path, "w") as f:
                    f.write(f"prefix={glib2_root}\n")
                    f.write(f"libdir=${{prefix}}/lib\n")
                    f.write(f"includedir=${{prefix}}/include\n\n")
                    f.write(f"Name: {desc}\n")
                    f.write(f"Description: {desc} (wrapper for glib2)\n")
                    f.write("Version: 2.88.0\n")
                    if pc_name == "libffi":
                        f.write(f"Libs: -L${{libdir}} -lffi\n")
                        f.write(f"Cflags: -I${{includedir}} -DFFI_STATIC_BUILD\n")
                    elif pc_name == "gio-unix-2.0":
                        f.write("Requires: glib-2.0 gobject-2.0 gmodule-2.0\n")
                        f.write(f"Libs: -L${{libdir}} -lgio-2.0\n")
                        f.write(f"Cflags: -I${{includedir}} -DG_INTL_STATIC_COMPILATION\n")
                    else:
                        f.write("Requires: glib-2.0\n")
                        f.write(f"Libs: -L${{libdir}} -l{pc_name}\n")
                        f.write(f"Cflags: -I${{includedir}}\n")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["girepository-1.0"]
        self.cpp_info.includedirs = ["include/gobject-introspection-1.0"]
        self.cpp_info.set_property("pkg_config_name", "gobject-introspection-1.0")
        # glib2 dependency is propagated via self.requires() in requirements()
