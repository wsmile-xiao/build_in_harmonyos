#!/usr/bin/env python3
"""Conan recipe for djvu2pdf — Convert DjVu files to PDF (shell script).

Shell script project, no compilation needed.
Installs the djvu2pdf bash script and djvu2pdf_toc_parser.py helper.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class Djvu2PdfConan(ConanFile):
    name = "djvu2pdf"
    version = "1.0"
    description = "Convert DjVu files to PDF format"
    license = "MIT"
    homepage = "https://github.com/vindvaki/djvu2pdf"
    url = ""

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "djvu2pdf", src=self.source_folder, dst=bin_dir)
        copy(self, "djvu2pdf_toc_parser.py", src=self.source_folder, dst=bin_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
