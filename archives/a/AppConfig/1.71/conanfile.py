#!/usr/bin/env python3
"""Conan recipe for AppConfig 1.71."""

import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AppConfigConan(ConanFile):
    name = "appconfig"
    version = "1.71"
    description = "Perl modules for reading configuration files and parsing command line arguments"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/pod/AppConfig"
    url = ""
    package_type = "header-library"
    settings = "os", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _perl(self):
        perl_pkg = self.dependencies["perl"].package_folder
        perl = os.path.join(perl_pkg, "bin", "perl")
        return perl if os.path.exists(perl) else "perl"

    def build(self):
        apply_conandata_patches(self)
        perl = self._perl()
        self.run(
            f'"{perl}" Makefile.PL PREFIX=/usr/local INSTALLDIRS=site',
            cwd=self.source_folder,
            env=["conanbuild", "conanrun"],
        )
        self.run("make -j1", cwd=self.source_folder, env=["conanbuild", "conanrun"])

    def package(self):
        self.run(
            f'make install DESTDIR="{self.package_folder}"',
            cwd=self.source_folder,
            env=["conanbuild", "conanrun"],
        )
        copy(self, "*.pm", src=os.path.join(self.source_folder, "lib"), dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []

        pm_files = glob.glob(os.path.join(self.package_folder, "**", "AppConfig.pm"), recursive=True)
        if pm_files:
            module_dir = os.path.dirname(pm_files[0])
            self.runenv_info.prepend_path("PERL5LIB", module_dir)
            self.buildenv_info.prepend_path("PERL5LIB", module_dir)
