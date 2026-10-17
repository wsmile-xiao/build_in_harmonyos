#!/usr/bin/env python3
"""Conan recipe for GNU units 2.27."""
import os
from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnitsConan(ConanFile):
    name = "units"
    version = "2.27"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/units/"
    description = "GNU units conversion calculator"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # HMDFS maps generated files to the storage service owner. Autoconf's
        # mode-0700 temporary directory then becomes unwritable by HiShell.
        configure = os.path.join(self.source_folder, "configure")
        text = open(configure, encoding="utf-8").read()
        text = text.replace("umask 077", "umask 000")
        save_path = configure
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--prefix=/usr",
            "--datarootdir=/usr/share",
            "--datadir=/usr/share",
            "--sharedstatedir=/var/lib",
        ])
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # The release has no independent tests/ directory. Exercise the core
        # converter directly while keeping network-backed currency checks out.
        binary = os.path.join(self.build_folder, "units")
        definitions = os.path.join(self.source_folder, "definitions.units")
        self.run(f"{binary} -t -f {definitions} '2 m' cm", cwd=self.build_folder)

    def package(self):
        copy(self, "units", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "units.1", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        for pattern in ("definitions.units", "elements.units", "locale_map.txt", "currency.units", "cpi.units", "metal_prices.units", "crypto.units"):
            copy(self, pattern, src=self.source_folder, dst=os.path.join(self.package_folder, "share", "units"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        data_dir = os.path.join(self.package_folder, "share", "units")
        # GNU units honors UNITSFILE at runtime; the compiled default points
        # at /usr/share/units, which is outside a Conan package.
        self.runenv_info.define("UNITSFILE", os.path.join(data_dir, "definitions.units"))
        self.runenv_info.define_path("UNITS_DATA_DIR", data_dir)
