#!/usr/bin/env python3
"""Conan recipe for ypserv 4.2 (NIS/YP server) on OpenHarmony PC.

ypserv is a GNU autotools C project whose release tarball already ships a
pre-generated `configure`, so no autoreconf/bootstrap step is needed (automake
is not available on the OHOS worker).

Dependencies, all consumed from the ohpcd registry and all static
(`libtirpc/1.3.7`, `libnsl/2.0.1`, `gdbm/1.23`, `libxcrypt/4.5.2`):

  libnsl/2.0.1     yp_* client API   (rpcsvc/ypclnt.h, rpcsvc/yp_prot.h,
                                      yp_master/yp_all/yp_get_default_domain)
  libtirpc/1.3.7   TI-RPC + XDR      (rpc/rpc.h, rpc/rpc_com.h, rpc/nettype.h);
                   also hard-required by libnsl, which degrades to a stub
                   library without it
  gdbm/1.23        DBM backend       (configure.ac: gdbm is the first entry of
                   the dbmliborder probe list); 1.23 is chosen over 1.24
                   because its binary is the static one, so no libgdbm.so has
                   to be resolved at run time (OHOS RPATH handling is fragile)
  libxcrypt/4.5.2  crypt()           (rpc.yppasswdd)

Two upstream binaries define their own YP XDR codecs (`ypserv/ypserv_xdr.c`
provides callback based `xdr_ypresp_all()`/`xdr_ypresp_maplist()`) while the
static `libnsl.a` ships rpcgen versions of the same symbols in `yp_xdr.o`.
With a shared libnsl on Linux the executable definition wins silently; with a
static library the duplicate must be tolerated explicitly, hence
``-Wl,--allow-multiple-definition`` (double checked: only these two symbols
collide, and ypserv's own definitions are the ones that must be used).

The nine patches in conandata.yml carry the OHOS/musl portability work; see
their `patch_description` fields and notes.md for the root cause of each one.

Upstream test suite (`lib/Makefile.am`: ``TESTS = test-securenets
test-ypserv_conf``) is run by build(); both tests pass.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class YpservConan(ConanFile):
    name = "ypserv"
    version = "4.2"
    description = "NIS (YP) server: ypserv, rpc.ypxfrd, rpc.yppasswdd, map tools and helpers"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/thkukuk/ypserv"
    url = "https://github.com/thkukuk/ypserv"
    topics = ("nis", "yp", "rpc", "tirpc", "daemon")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ypserv is supported only on Linux/OHOS")

    def requirements(self):
        # Hard requirements of upstream configure.ac:
        #   PKG_CHECK_MODULES([NSL],   [libnsl])     -> yp_* client interface
        #   PKG_CHECK_MODULES([TIRPC], [libtirpc])   -> RPC/XDR, HAVE_TIRPC
        #   AC_CHECK_LIB(gdbm, gdbm_open)            -> the DBM backend
        #   AC_CHECK_LIB(crypt, crypt)               -> rpc.yppasswdd
        self.requires("libnsl/2.0.1")
        self.requires("libtirpc/1.3.7")
        self.requires("gdbm/1.23")
        self.requires("libxcrypt/4.5.2")

    def layout(self):
        # In-source autotools build: configure/make run inside the source tree.
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # libnsl.pc and libtirpc.pc, consumed by PKG_CHECK_MODULES below.
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()

        tc = AutotoolsToolchain(self)
        # configure.ac locates the DBM backend and libcrypt with a bare
        # AC_CHECK_LIB (no pkg-config), so their search paths have to be handed
        # to autoconf explicitly through CFLAGS/LDFLAGS.  libnsl and libtirpc
        # are found through pkg-config (see build()).
        for name in ("gdbm", "libxcrypt"):
            dep = self.dependencies[name]
            tc.extra_cflags.append(f'-I{os.path.join(dep.package_folder, "include")}')
            tc.extra_ldflags.append(f'-L{os.path.join(dep.package_folder, "lib")}')
        # ypserv/ypserv_xdr.c and libnsl's yp_xdr.o define the same two XDR
        # entry points; the executable's definitions must win (see module doc).
        tc.extra_ldflags.append("-Wl,--allow-multiple-definition")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # HMDFS does not honour chmod +x reliably, so invoke configure through
        # the shell; `cd` inside the command avoids a conan-provided cwd, which
        # triggers a getcwd storm on the hmfs/hmdfs mount.
        self.run(
            f'cd "{src}" && umask 022 && '
            # PKG_CHECK_MODULES reads the .pc files emitted by PkgConfigDeps.
            # Without PKG_CONFIG_PATH the probes fall back to
            # AC_CHECK_LIB([nsl],[yp_match]) without -L/-I and fail.
            f'PKG_CONFIG_PATH="{self.generators_folder}'
            f'${{PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}}" '
            f'sh ./configure --prefix=/',
            env="conanbuild",
        )
        self.run(f'cd "{src}" && make -j1', env="conanbuild")
        # Upstream test suite: lib/test-securenets + lib/test-ypserv_conf.
        self.run(f'cd "{src}" && make -j1 check', env="conanbuild")

    def package(self):
        self.run(f'cd "{self.source_folder}" && make -j1 install '
                 f'DESTDIR="{self.package_folder}"', env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Executable package: daemons in sbin/, the map tools and helper
        # scripts in lib/yp/, plus rpcsvc/ypxfrd.x under include/.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["sbin", "lib/yp"]
        self.buildenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "sbin"))
        self.buildenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "lib", "yp"))
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "sbin"))
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "lib", "yp"))
