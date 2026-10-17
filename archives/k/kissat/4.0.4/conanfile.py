#!/usr/bin/env python3
"""Conan recipe for kissat 4.0.4 — compact incremental SAT solver.

kissat uses a custom configure script (not standard autotools):
- Does NOT support --prefix, --enable-static, --disable-shared
- Accepts CC=<compiler> as argument or from environment
- No 'make install' target — manual file copy required
- Build outputs: kissat (executable) + libkissat.a (static library)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, replace_in_file
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class KissatConan(ConanFile):
    name = "kissat"
    version = "4.0.4"
    description = "A compact incremental SAT solver by Armin Biere"
    license = "MIT"
    homepage = "https://github.com/arminbiere/kissat"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No dependencies — bare metal SAT solver, only links libm

    def validate(self):
        # kissat only produces static library — reject shared=True
        from conan.errors import ConanInvalidConfiguration
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "kissat only supports static library (libkissat.a)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: Use AutotoolsToolchain to generate compiler env (CC, CFLAGS)
        # kissat's configure picks up CC from environment
        tc = AutotoolsToolchain(self)
        # Do NOT add --prefix or --enable-static/--disable-shared
        # kissat's custom configure does not support these standard autotools options
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix shebang for OHOS (E165): /bin/sh -> /system/bin/sh
        # R32: platform guard required — only on OHOS
        configure_path = os.path.join(self.source_folder, "configure")
        if self.settings.os == "OHOS":
            replace_in_file(self, configure_path, "#!/bin/sh", "#!/system/bin/sh")
        # kissat uses a custom configure script (not autotools)
        # CC comes from AutotoolsToolchain env (R33 compliant)
        # Run from source_folder since AutotoolsToolchain creates build subfolder
        self.run("./configure", env="conanbuild", cwd=self.source_folder)
        self.run("make -j1", env="conanbuild", cwd=self.source_folder)

    def package(self):
        # kissat has no 'make install' target — manually copy build outputs
        build_dir = os.path.join(self.source_folder, "build")
        copy(self, "kissat", src=build_dir, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libkissat.a", src=build_dir, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "kissat.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["kissat"]
        self.cpp_info.system_libs = ["m"]  # bare metal solver, only links libm
        self.cpp_info.bindirs = ["bin"]  # kissat executable for consumers
