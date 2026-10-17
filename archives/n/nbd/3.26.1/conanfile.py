#!/usr/bin/env python3
"""Conan recipe for nbd (Network Block Device) 3.26.1.

nbd is a client/server for the Network Block Device protocol,
allowing remote block devices to be accessed over TCP.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class NbdConan(ConanFile):
    name = "nbd"
    version = "3.26.1"
    description = "Network Block Device client and server"
    license = "GPL-2.0"
    homepage = "https://github.com/NetworkBlockDevice/nbd"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("libnl/3.7.0")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # bison, flex, m4: use system-provided from HNP (no OHOS conan binary)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess cannot detect HarmonyOS; pass build/host explicitly
        tc.configure_args.append("--build=aarch64-linux-ohos")
        tc.configure_args.append("--host=aarch64-linux-ohos")
        # gnutls not yet available in ohpcd conan repo; disable for now
        tc.configure_args.append("--without-gnutls")
        # libnl available from conan (libnl/3.7.0)
        tc.configure_args.append("--with-libnl")
        # docbook2man not available; disable manpages
        tc.configure_args.append("--disable-manpages")
        tc.generate()

        # Generate .pc files for dependencies (needed by PKG_CHECK_MODULES)
        pc = PkgConfigDeps(self)
        pc.generate()

        # Also generate AutotoolsDeps for fallback env (CFLAGS/LDFLAGS/LIBS)
        deps = AutotoolsDeps(self)
        deps.generate()

        # Create gthread-2.0.pc wrapper: glib >= 2.32 merged gthread
        # into glib, but nbd's configure.ac still checks for it separately.
        glib_prefix = str(self.dependencies["glib"].package_folder)
        glib_libdir = os.path.join(glib_prefix, "lib")
        pc_content = (
            f"prefix={glib_prefix}\n"
            f"libdir=${{prefix}}/lib\n\n"
            f"Name: gthread-2.0\n"
            f"Description: GNU GThread Library (merged into glib-2.0 since 2.32)\n"
            f"Version: 2.84.0\n"
            f"Requires: glib-2.0\n"
            f"Libs: -L${{libdir}} -lgthread-2.0\n"
        )
        with open(os.path.join(self.generators_folder, "gthread-2.0.pc"), "w") as f:
            f.write(pc_content)

    def build(self):
        apply_conandata_patches(self)
        # Write ax_prog_bison.m4 to support/ (AC_CONFIG_MACRO_DIR)
        # Required by configure.ac; from autoconf-archive
        ax_prog_bison_m4 = '''# ===========================================================================
#      https://www.gnu.org/software/autoconf-archive/ax_prog_bison.html
# ===========================================================================
#serial 10
AC_DEFUN([AX_PROG_BISON], [
  AC_REQUIRE([AC_PROG_YACC])
  AC_REQUIRE([AC_PROG_EGREP])
  AC_CACHE_CHECK([if bison is the parser generator],[ax_cv_prog_bison],[
    AS_IF([$YACC --version 2>/dev/null | $EGREP -q '^bison '],
      [ax_cv_prog_bison=yes], [ax_cv_prog_bison=no])
  ])
  AS_IF([test "$ax_cv_prog_bison" = "yes"], [
      YACC="${YACC% -y} -o y.tab.c"
    ] m4_ifnblank([$1], [[$1]]),
    m4_ifnblank([$2], [[$2]])
  )
])
'''
        support_dir = os.path.join(self.source_folder, "support")
        os.makedirs(support_dir, exist_ok=True)
        with open(os.path.join(support_dir, "ax_prog_bison.m4"), "w") as f:
            f.write(ax_prog_bison_m4)
        # Source from git archive has no pre-generated configure; bootstrap.
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # Fix umask 077 → umask 022: HarmonyOS HMDFS rejects dirs created
        # with 0700 permissions (config.status temp dir creation fails)
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        # Delete broken .la files from conan dependencies (libnl, glib, etc.)
        # These have invalid dependency_libs paths that break libtool linking.
        for dep in self.dependencies.values():
            dep_folder = str(dep.package_folder) if dep.package_folder else ""
            if dep_folder:
                for la in glob.glob(os.path.join(dep_folder, "**", "*.la"), recursive=True):
                    try:
                        os.remove(la)
                    except OSError:
                        pass
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
