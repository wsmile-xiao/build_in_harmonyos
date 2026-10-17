#!/usr/bin/env python3
"""Conan recipe — lcmaps 1.6.7 (Autotools, without-GSI flavour)

Notes:
- Upstream offers a GSI flavour (default) that hard-requires globus/voms
  (configure: AC_GLOBUS + AC_CHECK_LIB([crypto])). Neither has a recipe in this
  repository, so we build the upstream-supported `--disable-gsi-mode` flavour,
  which produces liblcmaps_without_gsi plus the two small API libraries
  (liblcmaps_return_poolindex_without_gsi, liblcmaps_gss_assist_gridmap_without_gsi).
- Dependency closure is libc only:
  * dlopen/dlsym: musl provides the dl* API in libc; configure's hard check
    AC_CHECK_LIB([dl],[dlopen]) resolves on the OHOS toolchain (link probe
    `clang probe.c -ldl` passes; knowledge E013: add -ldl, musl dl in libc).
  * LEXLIB: pdl_yacc.c/pdl_lex.c ship pre-generated in the release tarball, so no
    flex/yacc is needed; configure sets LEXLIB='' when flex/lex is absent.
  * No autoreconf is run (the release tarball ships a working configure;
    knowledge E089: device aclocal is broken, tarball aclocal.m4 is complete).
- LCMAPS_ETC_HOME / LCMAPS_LIB_HOME / LCMAPS_MOD_HOME are compiled in via
  -D'...="@...@"' and are all derived from the (predictable) Conan package
  prefix: <prefix>/etc/lcmaps and <prefix>/lib/lcmaps. No device absolute paths.
- Shared delivery is intentional: LCMAPS evaluation plugins are dlopen()ed at
  runtime and downstream consumers (lcmaps-plugins-basic) consume the headers
  via pkg-config `lcmaps-basic-interface` and load/link liblcmaps_without_gsi.
- Symbol export: upstream uses NO -export-symbols / version script for the
  without-GSI libraries (liblcmaps_without_gsi_la_LDFLAGS is empty in
  src/Makefile.am), so the public API (lcmaps_init/lcmaps_run/lcmaps_term, ...)
  is exported by default — exactly what dlsym(RTLD_DEFAULT) consumers expect.
- Upstream has NO automated test suite (discovery: no check target /
  check_PROGRAMS in any Makefile.am; src/lcmaps_test.c is a manual GSI client in
  EXTRA_DIST; examples/ is a demo plugin). OHOS-specific verification lives in
  test_package/test.c: dlopen()/dlsym() of liblcmaps_without_gsi.so (the musl
  dynamic-loading adaptation point, E013) + compile-time check of the installed
  <lcmaps/lcmaps_version.h> API version macros + packaged .pc/header presence.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, mkdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LcmapsConan(ConanFile):
    name = "lcmaps"
    version = "1.6.7"
    description = (
        "LCMAPS: Local Credential MAPping Service — without-GSI flavour "
        "(core evaluation engine + poolindex/gss-assist-gridmap APIs)"
    )
    license = "Apache-2.0"
    url = "https://software.nikhef.nl/security/lcmaps/"
    homepage = "https://github.com/Nikhef-lcaae/lcmaps"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libc-only closure (musl: dl* in libc; LEXLIB optional and empty here)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Upstream-supported non-GSI flavour: drops globus/voms/openssl deps.
        tc.configure_args.append("--disable-gsi-mode")
        # E075: if C_INCLUDE_PATH/LIBRARY_PATH leak into the build environment,
        # pkg-config filters matching -I flags out of --cflags and configure
        # fails to find headers. Remove them from the build env snapshot.
        env = tc.environment()
        env.unset("C_INCLUDE_PATH")
        env.unset("CPLUS_INCLUDE_PATH")
        env.unset("LIBRARY_PATH")
        tc.generate()

    def build(self):
        # Platform-only patches: config.guess/config.sub HarmonyOS recognition
        # (uname -s reports "HarmonyOS", unrecognized by the 2023-06-23
        # config.guess, which then falls into its compile-fallback path that
        # fails on OHOS storage).
        apply_conandata_patches(self)
        # No autoreconf (E089): the release tarball carries a complete
        # configure/aclocal.m4 and pre-generated parser sources.
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Upstream installs the interface .pc files (lcmaps-basic-interface,
        # lcmaps-interface, lcmaps-globus-interface, lcmaps-openssl-interface)
        # into $(datadir)/pkgconfig (share/pkgconfig), while the flavour .pc
        # files (lcmaps-without-gsi, ...-without-gsi) go to lib/pkgconfig.
        # Relocate the share ones into lib/pkgconfig so a single PKG_CONFIG_PATH
        # libdir entry discovers the whole family.
        share_pc = os.path.join(self.package_folder, "share", "pkgconfig")
        lib_pc = os.path.join(self.package_folder, "lib", "pkgconfig")
        if os.path.isdir(share_pc):
            mkdir(self, lib_pc)
            for name in os.listdir(share_pc):
                if name.endswith(".pc") and not os.path.exists(
                    os.path.join(lib_pc, name)
                ):
                    shutil.move(os.path.join(share_pc, name), lib_pc)
            shutil.rmtree(share_pc, ignore_errors=True)
        # drop the now-empty share tree (only upstream doc files remain under
        # share/doc; leave those untouched)
        share_dir = os.path.join(self.package_folder, "share")
        if os.path.isdir(share_dir) and not os.listdir(share_dir):
            shutil.rmtree(share_dir, ignore_errors=True)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]  # headers live in include/lcmaps/
        self.cpp_info.libdirs = ["lib"]
        # aux libraries have LIBADD liblcmaps_without_gsi; order matters for
        # static consumers
        self.cpp_info.libs = [
            "lcmaps_return_poolindex_without_gsi",
            "lcmaps_gss_assist_gridmap_without_gsi",
            "lcmaps_without_gsi",
        ]
        self.cpp_info.set_property("pkg_config_name", "lcmaps-without-gsi")
