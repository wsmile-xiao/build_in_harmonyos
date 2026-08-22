#!/usr/bin/env python3
"""Conan recipe — aview 1.3.0rc1

aview is a high-quality ASCII-art image (PGM/PPM/PNG/BMP) viewer and
FLI/FLC animation player for terminals. Part of the AA-Project family
(same upstream as aalib/aafire/aa3d).

Build system: autotools (configure + make), depends on aalib (>= 1.4.0).
Produces command-line tools: aview, aaflip, and the asciiview wrapper script.
License: GPL-2.0-or-later.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AviewConan(ConanFile):
    name = "aview"
    version = "1.3.0rc1"
    description = ("ASCII-art image viewer and FLI/FLC animation player — "
                   "display PGM/PPM/PNG/BMP images as text art in terminal")
    license = "GPL-2.0-or-later"
    homepage = "https://aa-project.sourceforge.net/aview/"
    url = "https://aa-project.sourceforge.net/aview/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aalib/1.4p5")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aview supports Linux/OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # aview's configure insists on aalib-config --version, keep default.
        # The aalib dependency is pulled in via cpp_info (include/lib paths
        # injected by AutotoolsToolchain automatically).
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # OHOS: use bash explicitly (CONFIG_SHELL) — the default /system/bin/sh
        # cannot exec the autotools 'configure' script under SELinux adhoc_bin
        # domain (E009). Same established pattern as abcm2ps/acpid recipes.
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        src = self.source_folder.replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")
        # CC/CXX come from the conanbuild environment injected by
        # AutotoolsToolchain (profile tools.build:compiler_executables →
        # OHOS SDK clang). Only fall back to literal clang if unset.
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")

        # aview's configure (AM_PATH_AALIB) needs 'aalib-config' reporting
        # correct include/lib paths. The aalib binary published on ohpcd was
        # built with prefix "/", so its bundled aalib-config emits "-I//include"
        # (invalid). Generate a fixed copy pointing at the actual dependency
        # package dir, and expose it via AALIB_CONFIG + PATH.
        if "aalib" in self.dependencies:
            aalib = self.dependencies["aalib"]
            aalib_dir = aalib.package_folder.replace("\\", "/")
            prep_dir = os.path.join(self.build_folder, "prep-aalib")
            os.makedirs(prep_dir, exist_ok=True)
            fixed_cfg = os.path.join(prep_dir, "aalib-config")
            with open(fixed_cfg, "w", encoding="utf-8") as f:
                f.write(f"""#!/bin/sh
prefix={aalib_dir}
exec_prefix=${{prefix}}
usage="Usage: aalib-config [--prefix[=DIR]] [--libs] [--cflags]"
while test $# -gt 0; do
  case "$1" in
    --prefix) echo $prefix ;;
    --version) echo 1.4.0 ;;
    --cflags) echo -I${{prefix}}/include ;;
    --libs) echo -L${{prefix}}/lib -laa -lm ;;
    *) shift ;;
  esac
  shift
done
""")
            os.chmod(fixed_cfg, 0o755)
            d = f"export AALIB_CONFIG={fixed_cfg} PATH={prep_dir}:$PATH && "
        else:
            d = ""
        self.run(
            f"{d}cd '{src}' && CONFIG_SHELL={config_shell} CC={cc} CXX={cxx} "
            f"{config_shell} ./configure --prefix={prefix}",
            env="conanbuild",
        )
        self.run(
            f"cd '{src}' && CC={cc} CXX={cxx} make -j1",
            env="conanbuild",
        )

    def package(self):
        # Copy built binaries directly (same pattern as abcm2ps/acpid):
        # `make install` spawns a parallel jobserver via mkfifo which is
        # blocked under OHOS SELinux, so manual copy is deterministic.
        import shutil
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for name in ("aview", "aaflip"):
            p = os.path.join(self.source_folder, name)
            if os.path.isfile(p):
                shutil.copy(p, os.path.join(bin_dir, name))
                shutil.copymode(p, os.path.join(bin_dir, name))
        # asciiview is a shell script wrapper (installed to bin/ via make install)
        script = os.path.join(self.source_folder, "asciiview")
        if os.path.isfile(script):
            shutil.copy(script, os.path.join(bin_dir, "asciiview"))
            shutil.copymode(script, os.path.join(bin_dir, "asciiview"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []