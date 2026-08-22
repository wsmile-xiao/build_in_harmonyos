#!/usr/bin/env python3
"""Conan recipe — libfm-extra 1.3.2.1.

libfm-extra is the "extra" module of libfm (LXDE file manager library).
Only one source file (fm-xml-file.c) is compiled; build is done directly
with clang to avoid autotools/libtool issues on OHOS.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibfmextraConan(ConanFile):
    name = "libfm-extra"
    version = "1.3.2.1"
    description = "libfm-extra 1.3.2.1"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/lxde/libfm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.0")
        self.requires("gettext/0.22.5")

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply config.guess/config.sub patches for OHOS triplet support
        apply_conandata_patches(self)

        # Compile fm-xml-file.c directly — no autotools needed.
        # fm-xml-file.c only includes config.h when HAVE_CONFIG_H is defined;
        # the file has no HAVE_* feature macros, so we skip config.h entirely.
        glib = self.dependencies.host["glib"]
        cc = os.environ.get("CC", "clang")
        ar = os.environ.get("AR", "llvm-ar")

        include_dirs = " ".join([
            f"-I{self.source_folder}/src",
            f"-I{glib.package_folder}/include",
            f"-I{glib.package_folder}/include/glib-2.0",
            f"-I{glib.package_folder}/lib/glib-2.0/include",
        ])

        src = os.path.join(self.source_folder, "src", "extra", "fm-xml-file.c")
        obj = os.path.join(self.build_folder, "fm_xml_file.o")

        # GETTEXT_PACKAGE is normally defined in config.h; we skip config.h
        # so define it on the command line.  fm-xml-file.c also uses the
        # _() gettext macro which expands to g_dgettext(GETTEXT_PACKAGE, ...).
        self.run(
            f"{cc} -c {include_dirs} -fPIC "
            f'-DGETTEXT_PACKAGE=\\"libfm\\" '
            f"{src} -o {obj}"
        )

        lib_dir = os.path.join(self.build_folder, ".libs")
        os.makedirs(lib_dir, exist_ok=True)
        lib_path = os.path.join(lib_dir, "libfm-extra.a")
        self.run(f"{ar} rcs {lib_path} {obj}")

    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include", "libfm-1.0")
        os.makedirs(lib_dir)
        os.makedirs(inc_dir)

        shutil.copy2(
            os.path.join(self.build_folder, ".libs", "libfm-extra.a"),
            lib_dir,
        )

        src_dir = os.path.join(self.source_folder, "src")
        shutil.copy2(os.path.join(src_dir, "fm-extra.h"), inc_dir)
        shutil.copy2(
            os.path.join(src_dir, "extra", "fm-xml-file.h"),
            os.path.join(inc_dir, "fm-xml-file.h"),
        )

    def package_info(self):
        self.cpp_info.libs = ["fm-extra"]
