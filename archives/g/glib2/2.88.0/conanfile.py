#!/usr/bin/env python3
"""Conan recipe — glib2 2.88.0 (Meson).

GLib is the low-level core library of GNOME: data structures, object system
(GObject), main loop, I/O (GIO), threading, regex (via PCRE2) and more.
Adapted to HarmonyOS PC (aarch64). See notes.md for the platform adaptations.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Glib2Conan(ConanFile):
    name = "glib2"
    version = "2.88.0"
    description = "GLib — GNOME core C utility library (glib, gobject, gio, gmodule, gthread)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/glib"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # Generate .pc files for the conan deps (pcre2, zlib) so meson's
    # dependency('pcre2'/'zlib') finds them via pkg-config. MesonToolchain is
    # produced manually in generate() (customized project_options).
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib regex needs pcre2; GIO compression needs zlib. libffi (gobject
        # closures) is not published in the registry, so glib builds it from its
        # bundled meson subproject (subprojects/libffi.wrap) — see patch 0005.
        self.requires("pcre2/10.45")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # libffi is not published in the OHOS conan registry, so vendor it as a
        # meson subproject: place its source + the wrapdb meson build files into
        # subprojects/libffi-3.5.2/. glib then builds libffi offline (patch 0005).
        # Both URLs use github hosts so CI's mirror fallback rewrites them to a
        # mirror list (workers can't reach github.com directly); conan get()
        # accepts a url list and the .zip patch is auto-extracted.
        ffi = self.conan_data["libffi_subproject"]
        subprojects = os.path.join(self.source_folder, "subprojects")
        ffi_dir = os.path.join(subprojects, "libffi-3.5.2")
        get(self, url=ffi["source"]["url"], sha256=ffi["source"]["sha256"],
            destination=ffi_dir, strip_root=True)
        # wrapdb meson build files (zip, libffi-3.5.2/<meson.build>) overlay the source
        get(self, url=ffi["patch"]["url"], sha256=ffi["patch"]["sha256"],
            destination=subprojects)
        # glib unconditionally requires gettext/intl; musl has none, so vendor the
        # proxy-libintl subproject (glib falls back to it via allow_fallback).
        pintl = self.conan_data["proxy_libintl"]
        get(self, url=pintl["source"]["url"], sha256=pintl["source"]["sha256"],
            destination=os.path.join(subprojects, "proxy-libintl-0.5"), strip_root=True)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names (llvm-ar,
        # llvm-as, ...) that are NOT on its PATH — only the GNU binutils
        # (ar/as/strip/nm/ranlib) and ld.lld exist. meson probes these and aborts
        # at configure ("Unknown linker(s): llvm-ar"), and its name search does
        # not resolve bare names, so pin the real tools by ABSOLUTE PATH (resolved
        # from PATH) and drop the broken env values.
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
        # Conan's MesonToolchain defaults wrap_mode=nofallback, which blocks the
        # libffi subproject fallback (libffi is not in the registry; vendored in
        # subprojects/libffi-3.5.2/ by source()). nodownload re-enables fallback
        # to the pre-existing (vendored) subproject without allowing network wraps.
        tc.project_options["wrap_mode"] = "nodownload"
        # OHOS has no libmount / selinux / gettext (nls) in the toolchain sysroot.
        tc.project_options["libmount"] = "disabled"
        tc.project_options["selinux"] = "disabled"
        tc.project_options["nls"] = "disabled"
        # No gobject-introspection / man pages / gtk-doc / fuzzing on the target.
        tc.project_options["introspection"] = "disabled"
        tc.project_options["man-pages"] = "disabled"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["oss_fuzz"] = "disabled"
        # Build upstream tests; native OHOS/HarmonyOS runs them in build().
        tc.project_options["tests"] = "true"
        tc.project_options["installed_tests"] = "false"
        tc.generate()

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
                        'meson test -v -C "{}" --timeout-multiplier=16 '
                        "--no-rebuild --no-suite=failing".format(build_folder)
                    )

                meson.test = _ohos_meson_test

            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = [
            "glib-2.0",
            "gobject-2.0",
            "gio-2.0",
            "gmodule-2.0",
            "gthread-2.0",
            "ffi",
            # libglib-2.0.a references the g_libintl_* gettext stubs built by the
            # proxy-libintl subproject (installed as libintl.a); static consumers
            # must link it.
            "intl",
        ]
        # glib public headers live under include/glib-2.0; glibconfig.h under lib/glib-2.0/include.
        self.cpp_info.includedirs = ["include/glib-2.0", "lib/glib-2.0/include"]
        self.cpp_info.system_libs = ["m", "pthread", "dl", "rt"]
        self.cpp_info.set_property("pkg_config_name", "glib-2.0")
