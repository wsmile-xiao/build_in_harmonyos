#!/usr/bin/env python3
"""Conan recipe for polipo 1.1.1."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


def _required_copy(conanfile, pattern, *, src, dst, **kwargs):
    copied = copy(conanfile, pattern, src=src, dst=dst, **kwargs)
    if not copied:
        raise ConanException(
            f"Required package input {pattern!r} was not found under {src!r}"
        )
    return copied


class PolipoConan(ConanFile):
    name = "polipo"
    version = "1.1.1"
    description = "Small and fast caching web proxy"
    license = "MIT"
    homepage = "https://www.irif.fr/~jch/software/polipo/"
    url = homepage
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        self.run(
            f'make CC="{cc}" PREFIX=/usr/local '
            'LOCAL_ROOT="~/.local/share/polipo/www" '
            'CDEBUGFLAGS="-fPIC -O2" -j1 polipo',
            cwd=self.source_folder,
        )

    def package(self):
        www_dir = os.path.join(self.package_folder, "share", "polipo", "www")
        _required_copy(
            self,
            "polipo",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        _required_copy(
            self,
            "localindex.html",
            src=self.source_folder,
            dst=www_dir,
            keep_path=False,
        )
        os.replace(
            os.path.join(www_dir, "localindex.html"),
            os.path.join(www_dir, "index.html"),
        )
        _required_copy(
            self,
            "config.sample",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "polipo"),
            keep_path=False,
        )
        _required_copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
