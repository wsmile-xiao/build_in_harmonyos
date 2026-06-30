#!/usr/bin/env python3
"""Conan recipe — libpagemaker 0.0.3 (Autotools).

libpagemaker is a library for importing and converting PageMaker documents.
Part of the LibreOffice project.

This recipe enforces:
  R26: Static linking (--enable-static --disable-shared)
  R27: Dependencies use @ohpcd/stable
"""
import os
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LibpagemakerConan(ConanFile):
    name = "libpagemaker"
    version = "0.0.3"
    description = "Library for importing and converting PageMaker documents (LibreOffice project)"
    license = "MPL-2.0"
    homepage = "https://wiki.documentfoundation.org/DLP/Libraries/libpagemaker"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: Dependencies must use @ohpcd/stable
        self.requires("librevenge/0.0.5@ohpcd/stable")

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

        tc = AutotoolsToolchain(self)
        # R26: Static linking — build only static libraries
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # Disable -Werror: boost headers trigger -Wdeprecated-copy-with-user-provided-copy
        tc.configure_args.append("--disable-werror")
        # R26: Force static linking of all libraries (librevenge, libc++, etc.)
        # -static: libtool flag to prefer .a over .so for libtool libraries
        # -Wl,-Bstatic: linker flag to keep static mode for compiler-added libs (libc++, etc.)
        tc.extra_ldflags = ["-static", "-Wl,-Bstatic"]
        tc.generate()

        # Prepend wrapper to PATH and set PKG_CONFIG_PATH for dependencies
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        # Set PKG_CONFIG_PATH to include dependency pkgconfig directories
        for dep_name, dep in self.dependencies.items():
            pkgconfig_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkgconfig_dir):
                env.prepend_path("PKG_CONFIG_PATH", pkgconfig_dir)
        # R26: Also statically link libc++ (not in G3 skip_libs)
        # Use -l: syntax to force specific .a files from OHOS SDK
        env.append("LIBS", "-l:libc++.a -l:libc++abi.a")
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
        self.cpp_info.libs = ["pagemaker-0.0"]
        self.cpp_info.requires = ["librevenge::librevenge"]
