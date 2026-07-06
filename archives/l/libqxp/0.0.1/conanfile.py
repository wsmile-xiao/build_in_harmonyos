#!/usr/bin/env python3
"""Conan recipe — libqxp 0.0.1 (Autotools).

libqxp is a library for parsing QuarkXPress files.
Part of the LibreOffice project.

This recipe enforces:
  R26: Static linking (BUILD_SHARED_LIBS=OFF via --disable-shared --enable-static)
  R27: Dependencies use 
"""
import os
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LibqxpConan(ConanFile):
    name = "libqxp"
    version = "0.0.1"
    description = "Library for parsing QuarkXPress files (LibreOffice project)"
    license = "MPL-2.0"
    homepage = "https://wiki.documentfoundation.org/DLP/Libraries/libqxp"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: Dependencies must use 
        self.requires("librevenge/0.0.5")
        self.requires("icu/77.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
        # causing config.status to fail. Create a mktemp wrapper that fixes perms.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        # PkgConfigDeps: generate .pc files for dependencies (librevenge, icu)
        # so configure can find them via pkg-config
        pkg = PkgConfigDeps(self)
        pkg.generate()

        tc = AutotoolsToolchain(self)
        # R26: Static linking — build only static libraries
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-tests")  # Skip cppunit requirement for package build
        # ICU 77.1 requires C++17 for LocalOpenPointer template (auto non-type template parameter)
        tc.extra_cxxflags.append("-std=c++17")
        tc.generate()

        # Prepend wrapper to PATH
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("hmos_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libqxp")
        self.cpp_info.set_property("cmake_target_name", "libqxp::libqxp")
        self.cpp_info.set_property("pkg_config_name", "libqxp-0.0")

        lib = self.cpp_info.components["libqxp"]
        lib.libs = ["qxp-0.0"]
        lib.includedirs = ["include/libqxp-0.0"]
        lib.requires = ["librevenge::librevenge", "librevenge::stream", "icu::uc"]
