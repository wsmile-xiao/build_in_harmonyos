#!/usr/bin/env python3
"""Conan recipe for shared-mime-info 2.4 — freedesktop MIME database
builder (C, meson build, freedesktop source).

Adaptation notes:
- Meson build with Conan MesonToolchain + PkgConfigDeps (R33 compliant).
- AR injection: Conan MesonToolchain native file lacks 'ar' entry for
  OHOS llvm-ar — manually inject after tc.generate() (same as ATK recipe).
- test_tree_magic scoping fix: tests/meson.build references test_tree_magic
  (defined in src/meson.build inside `if gio.found()`) — meson subdir
  vars don't propagate to sibling subdirs, so define it at the ROOT
  meson.build before subdir('src') so it reaches tests/ too.
- -Dupdate-mimedb=false: don't run update-mime-database during install.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SharedMimeInfoConan(ConanFile):
    name = "shared-mime-info"
    version = "2.4"
    description = "Freedesktop.org shared MIME-info database"
    license = "GPL-2.0"
    homepage = "https://freedesktop.org/wiki/Software/shared-mime-info/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "application"

    def export_sources(self):
        return ["conandata.yml"]

    def requirements(self):
        self.requires("libxml2/2.15.3")
        self.requires("glib/2.84.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["update-mimedb"] = "false"
        tc.project_options["build-tests"] = "true"
        tc.project_options["wrap_mode"] = "nofallback"
        tc.generate()

        # Inject AR into Conan-generated meson native file [binaries] section
        # (Conan only injects c/cpp, not ar — OHOS llvm-ar at /data/service/hnp/bin)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        ar = (compilers.get("archive")
              or shutil.which("llvm-ar")
              or "/data/service/hnp/bin/llvm-ar")
        native_file = os.path.join(self.generators_folder,
                                   "conan_meson_native.ini")
        if os.path.exists(native_file):
            with open(native_file, "r") as nf:
                content = nf.read()
            if "ar = " not in content:
                content_new, n = re.subn(
                    r"(cpp = '[^']*')",
                    rf"\1\nar = '{ar}'",
                    content,
                    count=1,
                )
                if n:
                    with open(native_file, "w") as nf:
                        nf.write(content_new)

        # PkgConfigDeps: generate pkg-config files for libxml2/glib
        pkg = PkgConfigDeps(self)
        pkg.generate()

        # Copy glib sub-module .pc files (gio-2.0 etc.) — meson uses
        # pkg-config via native file, not env PKG_CONFIG_PATH
        import glob as _glob
        glib_pkg = self.dependencies["glib"]
        glib_pkgconfig = os.path.join(glib_pkg.package_folder, "lib",
                                       "pkgconfig")
        if os.path.isdir(glib_pkgconfig):
            for pc in _glob.glob(os.path.join(glib_pkgconfig, "*.pc")):
                dst_pc = os.path.join(self.generators_folder,
                                     os.path.basename(pc))
                if not os.path.exists(dst_pc):
                    shutil.copy2(pc, dst_pc)

    def build(self):
        # Fix test_tree_magic scoping: define at ROOT meson.build
        # so tests/meson.build can see the variable
        mb = os.path.join(self.source_folder, "meson.build")
        if os.path.isfile(mb):
            with open(mb, "r") as f:
                s = f.read()
            anchor = "subdir('src')"
            decl = ("test_tree_magic = executable('tree-magic', "
                    "'src/test-tree-magic.c', "
                    "dependencies: [dependency('glib-2.0')], "
                    "install: false)\n")
            if anchor in s and "test_tree_magic = executable" not in s.split(
                    anchor)[0]:
                with open(mb, "w") as f:
                    f.write(s.replace(anchor, decl + anchor, 1))

        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()

    def package(self):
        src = self.source_folder
        # Locate the built binary in the meson build directory
        umd = None
        for root, _dirs, files in os.walk(self.build_folder):
            if "update-mime-database" in files:
                umd = os.path.join(root, "update-mime-database")
                break
        if not umd:
            raise ConanException("update-mime-database binary missing")
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        shutil.copy2(umd, os.path.join(self.package_folder, "bin",
                                       "update-mime-database"))
        data = os.path.join(src, "data")
        if os.path.isdir(data):
            shutil.copytree(data, os.path.join(self.package_folder, "data"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
