#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Acpi, acpi, 1.8, acpi 1.8, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AcpiConan(ConanFile):
    name = "acpi"
    version = "1.8"
    description = "acpi 1.8"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        # ncurses: tc.configure_args.append("--without-shared")  # R4
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS workaround: mktemp -d creates dirs with wrong permissions
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                'tmp= false &&')
        # Fix: version() and usage() should return 0, not 1 (upstream bug)
        main_c_path = os.path.join(self.source_folder, "main.c")
        if os.path.isfile(main_c_path):
            replace_in_file(self, main_c_path,
                'warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\\n"\n);\n\treturn 1;',
                'warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\\n"\n);\n\treturn 0;')
            replace_in_file(self, main_c_path,
                'Report bugs to Michael Meskes <meskes@debian.org>.\\n"\n);\n\treturn 1;',
                'Report bugs to Michael Meskes <meskes@debian.org>.\\n"\n);\n\treturn 0;')
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # acpi is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
