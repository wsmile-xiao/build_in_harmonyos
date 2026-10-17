#!/usr/bin/env python3
"""Conan recipe for WCSLIB 8.4 — Autotools (configure + make).

WCSLIB is an implementation of the FITS World Coordinate System standard.
Built as a static library with Fortran and PGPLOT disabled, CFITSIO optional.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WcslibConan(ConanFile):
    name = "wcslib"
    version = "8.4"
    description = "An implementation of the FITS World Coordinate System standard"
    license = "LGPL-3.0-or-later"
    homepage = "https://www.atnf.csiro.au/people/mcalabre/WCS/"
    url = ""  # CI fills this

    package_type = "library"

    # R32: settings.os must check in ("Linux", "OHOS"), never == "Linux"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # WCSLIB's cfitsio dependency is optional and disabled (--without-cfitsio)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: AutotoolsToolchain provides compiler/flags — no bare shell vars
        tc = AutotoolsToolchain(self)
        # R26: static by default for system-name libraries
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Disable optional dependencies: Fortran, PGPLOT, CFITSIO
        tc.configure_args.append("--disable-fortran")
        tc.configure_args.append("--without-pgplot")
        tc.configure_args.append("--without-cfitsio")
        tc.generate()

    def build(self):
        src = self.source_folder

        # 1. Apply all conandata patches (GNUmakefile + config.guess/config.sub).
        # The config.guess/config.sub patches replace the original 2018 versions
        # with 2023 versions that include HarmonyOS (__OHOS__) detection.
        # These must be applied BEFORE autoconf, since autoconf uses config.guess
        # to determine the build/host platform.
        apply_conandata_patches(self)

        # 2. Run autoconf to generate the configure script.
        # The tarball ships only configure.ac (no pre-generated configure).
        # We use autoconf (not autoreconf) because configure.ac doesn't use
        # any AM_ automake macros — there are no Makefile.am files, only
        # GNUmakefile. This avoids the broken aclocal (automake 1.17 missing
        # Perl modules) that autoreconf would invoke.
        self.run("autoconf -fi", cwd=src)

        # Fix HarmonyOS umask issue in configure AND config.status: autoconf
        # generates both with (umask 077 && mktemp -d) to create temp
        # directories, but on HarmonyOS HMDFS this produces drwx--S---
        # (missing owner-execute due to SGID inheritance), causing
        # "Permission denied" when writing subs1.awk. Changing to umask 000
        # produces drwxrws--x which is writable.
        configure_script = os.path.join(src, "configure")
        if os.path.isfile(configure_script):
            replace_in_file(
                self,
                configure_script,
                "(umask 077 && mktemp",
                "(umask 000 && mktemp",
            )
            replace_in_file(
                self,
                configure_script,
                '(umask 077 && mkdir "$tmp")',
                '(umask 000 && mkdir "$tmp")',
            )

        autotools = Autotools(self)
        autotools.configure()

        # Copy generated files from build dir to source dir.
        # wcslib's GNUmakefile uses `include makedefs` (relative path),
        # so make must run from the source dir where GNUmakefile lives.
        # But configure generates makedefs/wcslib.pc/wcsconfig*.h in the
        # build dir. Copy them to the source dir so make can find them.
        for fname in [
            "makedefs", "wcslib.pc", "wcsconfig.h", "wcsconfig_f77.h",
            "wcsconfig_tests.h", "wcsconfig_utils.h", "config.log",
            "config.status",
        ]:
            src_file = os.path.join(self.build_folder, fname)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, os.path.join(src, fname))

        # Fix install-sh path: makedefs sets INSTALL to ./config/install-sh
        # which is relative to the top-level dir, but GNUmakefile recurses
        # into C/, utils/, and doxygen/ subdirectories where the relative
        # path breaks. Copy install-sh to subdirectory config/ dirs.
        config_dir = os.path.join(src, "config")
        install_sh = os.path.join(config_dir, "install-sh")
        for subdir in ["C", "utils", "doxygen"]:
            sub_config = os.path.join(src, subdir, "config")
            os.makedirs(sub_config, exist_ok=True)
            dst = os.path.join(sub_config, "install-sh")
            if not os.path.isfile(dst):
                shutil.copy2(install_sh, dst)
                os.chmod(dst, 0o755)

        # Run make from source dir (where GNUmakefile lives).
        # Use -j1 to avoid HMDFS fifo issues with make jobserver.
        self.run("make -j1", cwd=src)

    def package(self):
        # Run make install from source dir with DESTDIR pointing to the
        # Conan package folder. The prefix is set by AutotoolsToolchain.
        # Ignore doxygen install errors (missing wcslib.pdf is non-critical).
        self.run(
            f"make install DESTDIR={self.package_folder}",
            cwd=self.source_folder,
            ignore_errors=True,
        )

    def package_info(self):
        # The library is installed as libwcs-8.4.a with symlink libwcs.a
        # pkg-config uses -lwcs, so the Conan lib name is "wcs"
        self.cpp_info.libs = ["wcs"]
        self.cpp_info.system_libs = ["m"]
        # Headers are installed to include/wcslib-8.4/ with symlink include/wcslib
        # The symlink may not survive packaging, so use the versioned dir
        self.cpp_info.includedirs = ["include/wcslib-8.4"]
