#!/usr/bin/env python3
"""Conan recipe for GNU UnRTF 0.21.10."""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnrtfConan(ConanFile):
    name = "unrtf"
    version = "0.21.10"
    description = "GNU UnRTF converts Rich Text Format documents to HTML, text, LaTeX and other formats"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/unrtf/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--datarootdir=${prefix}/share")
        tc.generate()

    def _patch_configure_umask(self):
        configure_path = f"{self.source_folder}/configure"
        replacements = {
            '(umask 077 && mktemp -d "./confXXXXXX")': '(umask 022 && mktemp -d "./confXXXXXX")',
            '(umask 077 && mkdir "$tmp")': '(umask 022 && mkdir "$tmp")',
        }
        with open(configure_path, "r", encoding="utf-8") as f:
            content = f.read()
        changed = False
        for old, new in replacements.items():
            if old in content:
                content = content.replace(old, new)
                changed = True
        if not changed:
            raise ConanException("Expected configure umask patterns not found")
        with open(configure_path, "w", encoding="utf-8") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        # Build-time HMDFS config.status temp-dir permission fix; keep generated configure out of persistent patches.
        self._patch_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
