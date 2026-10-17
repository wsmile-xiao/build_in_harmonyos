#!/usr/bin/env python3
"""Conan recipe — libpeas 2.2.1 (Meson).

libpeas is a GObject-based plugin engine: it allows applications to load
plugins (C via GModule, plus optional Python/Lua/GJS loaders) that extend
the app through GObject interfaces. Adapted to HarmonyOS PC (aarch64).
See notes.md for the platform adaptations.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Libpeas2Conan(ConanFile):
    name = "libpeas2"
    version = "2.2.1"
    description = "libpeas — GObject plugin engine (peas-2)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libpeas"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    # NOTE: libpeas MUST be built shared. The C loader dlopen()s plugin
    # modules; with a static libpeas each module gets its own copy of
    # PeasObjectModule/introspection GTypes and re-registers them ->
    # "cannot register existing type" -> test-extension-set failures.
    # PkgConfigDeps so meson's dependency('glib-2.0'/'girepository-2.0')
    # resolves through the generated .pc files.
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib >= 2.86 required by libpeas 2.2.1's meson.build. The 2.88.3
        # recipe exposes the girepository-2.0 component (libgirepository-2.0
        # ships inside glib since 2.78) which the C loader / gmodule probing
        # and the upstream test framework rely on.
        self.requires("glib/2.88.3")
        # peas-i18n.c (patch 0001) calls libintl_bindtextdomain directly;
        # those symbols live in the static proxy-libintl archive, which the
        # generated glib-2.0.pc does not pull in for shared linking.
        self.requires("proxy-libintl/0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Same fix as glib 2.88.0: CI exports AR/AS/STRIP/NM/RANLIB as
        # llvm-* names that are NOT on PATH; meson aborts at configure
        # ("Unknown linker(s): llvm-ar"). Pin the real tools by absolute path.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(f"Required build tools not found in PATH: {', '.join(missing)}")
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["wrap_mode"] = "nofallback"
        # Optional loaders: python3/gjs/lua51 are not published on OHOS.
        tc.project_options["python3"] = "false"
        tc.project_options["gjs"] = "false"
        tc.project_options["lua51"] = "false"
        # GIR/typelib generation needs g-ir-scanner (E212: _giscanner.so
        # cannot dlopen on HarmonyOS) — disabled; tests build without GIRs
        # via patch 0003.
        tc.project_options["introspection"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["vapi"] = "false"
        # Build upstream tests; run them in build() on native OHOS.
        # (Upstream gates tests/ on generate_gir; patch 0003 relaxes it.)
        tc.generate()

        # gnome.genmarshal / gnome.compile_resources resolve their helpers
        # through pkg-config variables (glib_genmarshal, glib_compile_resources)
        # that Conan's PkgConfigDeps glib-2.0.pc does not carry. Append them,
        # pointing at the helpers shipped inside the glib package itself.
        glib_pkg = self.dependencies["glib"]
        bindir = glib_pkg.cpp_info.bindirs[0]
        # The glib package helper binaries dynamically link libglib-2.0.so
        # from the same package. Meson invokes them through the pkg-config
        # variables below, but env vars we set in generate() do not reach
        # ninja's subcommands — so wrap each helper in a script that sets
        # LD_LIBRARY_PATH itself.
        glib_libdir = glib_pkg.cpp_info.libdirs[0]
        tools_dir = os.path.join(self.generators_folder, "glib-tools")
        os.makedirs(tools_dir, exist_ok=True)
        wrappers = {}
        for helper in ("glib-genmarshal", "glib-compile-resources"):
            wrapper = os.path.join(tools_dir, helper)
            with open(wrapper, "w") as f:
                f.write("#!/bin/sh\n")
                f.write('LD_LIBRARY_PATH="{0}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"\n'.format(glib_libdir))
                f.write('export LD_LIBRARY_PATH\n')
                f.write('exec "{}/{}" "$@"\n'.format(bindir, helper))
            os.chmod(wrapper, 0o755)
            wrappers[helper] = wrapper
        for pc_name in ("glib-2.0", "gio-2.0"):
            pc = os.path.join(self.generators_folder, pc_name + ".pc")
            if os.path.exists(pc):
                with open(pc, "a") as f:
                    f.write("\nglib_genmarshal={}\n".format(wrappers["glib-genmarshal"]))
                    f.write("glib_compile_resources={}\n".format(wrappers["glib-compile-resources"]))
        # peas-i18n.c calls libintl_* directly; add -lintl to the link line
        # meson derives from glib-2.0.pc (Conan's generated pc omits intl).
        intl_pkg = self.dependencies["proxy-libintl"]
        intl_libdir = intl_pkg.cpp_info.libdirs[0]
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.exists(pc):
            with open(pc) as f:
                content = f.read()
            content = content.replace(
                "Libs: -L",
                'Libs: -L"{}" -lintl -L'.format(intl_libdir),
                1,
            )
            with open(pc, "w") as f:
                f.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries are not runnable on the build host)"
            )
        else:
            if hasattr(os, "uname") and os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder

                def _ohos_meson_test():
                    self.run(
                        'meson test -v -C "{}" --timeout-multiplier=16'.format(build_folder)
                    )

                meson.test = _ohos_meson_test

            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libpeas-2")
        self.cpp_info.libs = ["peas-2"]
        self.cpp_info.includedirs = ["include/libpeas-2"]
        self.cpp_info.requires = ["glib::glib", "glib::gobject", "glib::gio", "glib::gmodule", "proxy-libintl::proxy-libintl"]
