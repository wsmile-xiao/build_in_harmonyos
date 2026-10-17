#!/usr/bin/env python3
"""Conan recipe — libgepub 0.7.3 (Meson).

GObject-based EPUB handling library (GNOME). Headless core only:
-Dwidget=false drops the WebKit2GTK GepubWidget and the GTK interactive
demo in tests/ (needs display + webkit, unavailable on OHOS);
-Dintrospection=false (no gobject-introspection scanner on OHOS).

Upstream tests/test-gepub.c defines 7 TEST() cases (test_open/read/
root_file/doc_name/doc_resources/doc_spine/doc_toc) that exercise only
GepubArchive/GepubDoc; the surrounding harness needs gtk+-3.0 + webkit +
display + gtk_main, so meson registers zero test() targets. The 7 cases
are executed headlessly in test_package/upstream_headless.c against an
offline synthetic EPUB; consumer coverage comes from test_package/test.c
(16 real-API assertions over the same synthetic EPUB).
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class LibgepubConan(ConanFile):
    name = "libgepub"
    version = "0.7.3"
    description = "GObject-based library for handling EPUB documents"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgepub"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libgepub is validated only for Linux/OHOS")

    def requirements(self):
        # glib/2.84.0.1.1 shared: same pin as the libsoup3/3.6.5-r3 chain so
        # libgepub and libsoup share one GObject type system (a second glib
        # copy causes "cannot register existing type" SIGABRT, libsoup3 r3
        # precedent).
        self.requires("glib/2.84.0.1.1", options={"shared": True},
                      transitive_headers=True, transitive_libs=True)
        self.requires("libsoup3/3.6.5-r3", transitive_libs=True)
        self.requires("libxml2/2.15.3.1", transitive_libs=True)
        self.requires("libarchive/3.8.7", transitive_libs=True)

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders here
        # (same pattern as the glib/libsoup3 recipes in this repo).
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def build_requirements(self):
        # True-machine/CI worker sandboxes have no system meson
        # (/bin/sh: meson: inaccessible or not found); pull it from the
        # artifact repo (c-stdaux/gxr/gulkan precedent: meson/1.11.0).
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Same toolchain fix as the glib/libsoup3 recipes: the CI worker
        # exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are NOT on PATH;
        # meson probes these and aborts at configure. Pin the real tools by
        # absolute path and drop the broken env values.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(f"Required build tools not in PATH: {', '.join(missing)}")
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # Never strip shared libs: the OHOS loader checks the .codesign
        # section hash against file content, strip breaks it and dlopen fails
        # with Permission denied (libsoup3 recipe precedent).
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Headless core: no WebKit widget/GTK demo, no introspection scanner
        # (both are boolean options in upstream meson_options.txt).
        tc.project_options["widget"] = "false"
        tc.project_options["introspection"] = "false"
        # The glib package's own lib/pkgconfig holds .pc files PkgConfigDeps
        # does not generate; a prefix-fixed copy dir guards against
        # --prefix=/ .pc files resolving to /include, /lib (libsoup3 r3 fix).
        extra_pc = []
        if self.dependencies.get("glib"):
            glib_pkg = self.dependencies["glib"].package_folder
            extra_pc.append(os.path.join(glib_pkg, "lib", "pkgconfig"))
            pc_fix_dir = os.path.join(self.build_folder, "glib-pc-fix")
            os.makedirs(pc_fix_dir, exist_ok=True)
            for pc in os.listdir(os.path.join(glib_pkg, "lib", "pkgconfig")):
                if not pc.endswith(".pc"):
                    continue
                src = os.path.join(glib_pkg, "lib", "pkgconfig", pc)
                dst = os.path.join(pc_fix_dir, pc)
                with open(src, "r", encoding="utf-8") as fh:
                    text = fh.read()
                text = re.sub(r"^prefix=.*$", f"prefix={glib_pkg}", text, count=1, flags=re.M)
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(text)
            extra_pc.insert(0, pc_fix_dir)
            glib_bin = os.path.join(glib_pkg, "bin")
            if os.path.isdir(glib_bin):
                self.buildenv_info.prepend_path("PATH", glib_bin)
        tc.pkg_config_path = os.pathsep.join([tc.pkg_config_path] + extra_pc)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream evidence is emitted by test_package/test() AFTER running
        # ./upstream_headless (7/7 headless-ported TESTs). Nothing is printed
        # here so a stale no_tests/0 marker can never shadow the real result.

    def package(self):
        meson = Meson(self)
        meson.install()
        # meson install rewrites DT_RUNPATH in .dynstr, changing .so content
        # so the link-time .codesign hash mismatches and the OHOS loader
        # refuses dlopen (Permission denied). Overwrite the installed .so
        # with the pristine just-linked build-tree copy (libsoup3 precedent).
        for _lib in ("libgepub-0.7.so.0.0.0",):
            _src = os.path.join(self.build_folder, "libgepub", _lib)
            _dst = os.path.join(self.package_folder, "lib", _lib)
            if os.path.exists(_src):
                shutil.copy2(_src, _dst)

    def package_info(self):
        self.cpp_info.libs = ["gepub-0.7"]
        # Headers install flat to include/libgepub-0.7/*.h (gepub.h,
        # gepub-archive.h, gepub-doc.h, gepub-text-chunk.h plus config.h;
        # gepub.h includes <config.h>). Consumers include <gepub.h> with
        # -I include/libgepub-0.7 (Arch file list evidence).
        self.cpp_info.includedirs = ["include", "include/libgepub-0.7"]
        self.cpp_info.set_property("pkg_config_name", "libgepub-0.7")
        self.cpp_info.set_property("cmake_file_name", "libgepub-0.7")
        self.cpp_info.set_property("cmake_target_name", "libgepub-0.7::libgepub-0.7")
        # Public headers include glib/gio/gobject headers; CMakeDeps
        # generates empty data for the TRANSITIVE glib dep (conan 2.29), so
        # expose glib's include dirs + libs here for consumers (same pattern
        # as the libsoup3 recipe). Guarded: package_folder may be None while
        # the graph is being computed (test_package requires glib explicitly
        # as well, so it never hard-depends on this fallback).
        glib = self.dependencies.get("glib")
        if glib and glib.package_folder:
            self.cpp_info.includedirs.append(os.path.join(glib.package_folder, "include"))
            self.cpp_info.includedirs.append(os.path.join(glib.package_folder, "include", "glib-2.0"))
            self.cpp_info.includedirs.append(os.path.join(glib.package_folder, "lib", "glib-2.0", "include"))
            self.cpp_info.libdirs.append(os.path.join(glib.package_folder, "lib"))
            for _lib in ("glib-2.0", "gobject-2.0", "gio-2.0", "gmodule-2.0", "gthread-2.0"):
                if _lib not in self.cpp_info.libs:
                    self.cpp_info.libs.append(_lib)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(glib.package_folder, "lib"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
