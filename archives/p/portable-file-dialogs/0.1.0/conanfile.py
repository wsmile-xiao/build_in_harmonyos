#!/usr/bin/env python3
"""Conan recipe — portable-file-dialogs 0.1.0

Header-only C++11 library wrapping native OS file/message dialogs
(Windows Vista+, macOS osascript, Linux zenity/kdialog).
License: WTFPL-2.0. No build stage (v12.21 headeronly variant A).
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PortableFileDialogsConan(ConanFile):
    name = "portable-file-dialogs"
    version = "0.1.0"
    description = "Portable C++11 wrappers for native OS file/message dialogs (single header)"
    license = "WTFPL"
    homepage = "https://github.com/samhocevar/portable-file-dialogs"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # Header-only: no compile step. build() kept as patch application only —
    # patches: {} so this is a no-op (no fabricated build logs, R34).
    def build(self):
        apply_conandata_patches(self)

    def package(self):
        import os
        import shutil
        inc = os.path.join(self.package_folder, "include")
        os.makedirs(inc, exist_ok=True)
        src_hdr = os.path.join(self.source_folder, "portable-file-dialogs.h")
        self.output.info(f"pfd package: source_folder={self.source_folder}")
        shutil.copy2(src_hdr, os.path.join(inc, "portable-file-dialogs.h"))
        lic = os.path.join(self.source_folder, "COPYING")
        if os.path.exists(lic):
            os.makedirs(os.path.join(self.package_folder, "licenses"), exist_ok=True)
            shutil.copy2(lic, os.path.join(self.package_folder, "licenses", "COPYING"))

    def package_id(self):
        self.info.clear()  # header-only: single package_id regardless of settings

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
