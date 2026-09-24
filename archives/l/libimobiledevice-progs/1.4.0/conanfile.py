#!/usr/bin/env python3
"""Conan recipe for libimobiledevice-progs 1.4.0 — idevice* command-line tools.

The libimobiledevice project builds its library AND its user-facing
command-line utilities (idevice_id, ideviceinfo, idevicesyslog, ...) from a
single autotools source tree.  This package (package_type="application")
delivers the 21 tools in bin/ and deliberately drops the library, headers and
pkg-config files installed by upstream's catch-all install rules (same shape
as the libcpuid-tool 0.8.0 package).  The published shared library package
remains libimobiledevice/1.3.0 on the registry; the tools here link the
1.4.0 tree statically so they stay self-contained.

Dependencies (configure.ac PKG_CHECK_MODULES of 1.4.0, all on the registry):
  - libusbmuxd-2.0 >= 2.0.2  -> libusbmuxd/2.0.2
  - libplist-2.0  >= 2.3.0   -> libplist/2.3.0
  - libimobiledevice-glue-1.0 >= 1.3.0 -> libimobiledevice-glue/1.3.0
  - libtatsu-1.0  >= 1.0.3   -> libtatsu/1.0.5
  - openssl (default SSL backend) -> openssl/1.1.1w
  - readline (optional, afcclient) -> readline/8.3
libplist is pinned to 2.3.0 because libimobiledevice/1.3.0,
libimobiledevice-glue/1.3.0 and libtatsu/1.0.5 all require that exact
version (a 2.7.0 pin here would split the dependency graph).

OHOS adaptations (family conventions proven by libimobiledevice/1.3.0,
libimobiledevice-glue/1.3.0 and libtatsu/1.0.5):
  - mktemp wrapper: autoconf AS_TMPDIR uses `umask 077 && mktemp -d` which
    creates dirs with drwx--S--- on HMDFS (setgid + MAC), causing
    config.status to fail writing subs*.awk.  A fake mktemp returning
    failure forces the mkdir fallback (E114).
  - umask 077 -> 022 rewrite in the generated configure script (same as
    libimobiledevice/1.3.0): the mkdir fallback path also inherits the
    restrictive umask and config.status then cannot write subs*.awk.
  - --build=aarch64-unknown-linux-gnu: config.guess does not know OHOS.
  - Explicit CC/CXX injection: AutotoolsToolchain does not export CC and
    the device has no `cc` symlink (ccd2iso lesson).
  - Broken *.la in dependency packages (libdir='//lib') make libtool
    recurse into "not a valid libtool archive" (libimobiledevice/1.3.0
    lesson): dependency .la files are renamed to *.la.bak so libtool links
    the static archives directly.
  - LD_LIBRARY_PATH: OHOS loader has no default search path for
    conan-cached shared libs; configure conftest programs need it.
  - make -j1: parallel make hits the HMDFS jobserver fifo EPERM (R9).
  - Static build (--disable-shared --enable-static) so the tools in bin/
    do not depend on a dropped lib/ directory after packaging.
"""
import glob
import os
import shutil
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.scm import Version


class LibimobiledeviceProgsConan(ConanFile):
    name = "libimobiledevice-progs"
    version = "1.4.0"
    description = ("Command-line utilities (idevice_id, ideviceinfo, idevicesyslog, ...) "
                   "from the libimobiledevice project")
    license = "LGPL-2.1-or-later"
    homepage = "https://libimobiledevice.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libimobiledevice-progs is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # configure.ac of 1.4.0: LIBUSBMUXD_VERSION=2.0.2, LIBPLIST_VERSION=2.3.0,
        # LIMD_GLUE_VERSION=1.3.0, LIBTATSU_VERSION=1.0.3; openssl is the default
        # SSL backend; readline is optional (afcclient only, auto-detected).
        self.requires("libusbmuxd/2.0.2")
        self.requires("libplist/2.3.0")
        self.requires("libimobiledevice-glue/1.3.0")
        self.requires("libtatsu/1.0.5")
        self.requires("openssl/1.1.1w")
        self.requires("readline/8.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC);
        # a fake mktemp that fails forces autoconf AS_TMPDIR onto mkdir.
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

        # Dependency *.la files carry libdir='//lib' (conan autotools prefix
        # handling defect); libtool recursion then fails with "not a valid
        # libtool archive".  Rename them so libtool links the .a archives.
        # (cpp_info.libdirs may contain None entries for deps that do not
        # declare their layout — filter them.)
        for dep in self.dependencies.values():
            for libdir in (dep.cpp_info.libdirs or []):
                if not libdir or not dep.package_folder:
                    continue
                for la in glob.glob(os.path.join(dep.package_folder, libdir, "*.la")):
                    os.rename(la, la + ".bak")

        # AutotoolsDeps: feed -I/-L/-l from the dependency packages.
        AutotoolsDeps(self).generate()
        # PkgConfigDeps: generate .pc files for the configure PKG_CHECK_MODULES
        # calls (libusbmuxd-2.0, libplist-2.0, libimobiledevice-glue-1.0,
        # libtatsu-1.0, openssl, readline).
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # config.guess does not recognize OHOS (libplist family lesson).
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # Force the openssl SSL backend (no gnutls/libtasn1 on OHOS).
        tc.configure_args.append("--enable-openssl")
        # No python/cython bindings in a tools package.
        tc.configure_args.append("--without-cython")
        # Static build: the tools must not depend on the lib/ directory that
        # packaging drops (libcpuid-tool convention).
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        # OHOS loader has no default search path for conan-cached shared
        # libs; configure conftest programs need LD_LIBRARY_PATH.
        for dep in self.dependencies.values():
            for libdir in (dep.cpp_info.libdirs or []):
                if not libdir or not dep.package_folder:
                    continue
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        # The 1.4.0 tools (afcclient/idevicecrashreport/ideviceimagemounter)
        # call plist_dict_get_uint()/plist_dict_copy_uint(), added in
        # libplist 2.6.0.  The registry ships libplist/2.3.0 (the version the
        # whole libimobiledevice family is pinned to), so compile the
        # verbatim backport from patch 0001 (tools/plist_dict_compat.h).
        # The macro is only defined for libplist < 2.6.0 so the real library
        # functions are used once the registry ships a newer libplist.
        plist_version = str(self.dependencies["libplist"].ref.version)
        if Version(plist_version) < "2.6.0":
            env.append("CPPFLAGS", "-DLIBPLIST_LT_2_6=1")
        # AutotoolsToolchain does not export CC and the device has no `cc`
        # symlink: inject the toolchain explicitly (ccd2iso lesson).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        env.define("CC", compilers.get("c", "clang"))
        env.define("CXX", compilers.get("cpp", "clang++"))
        env.vars(self, scope="build").save_script("hmos_env")

    def build(self):
        # OHOS sandbox umask 077 makes config.status fail writing subs*.awk
        # (librrd/ccd2iso/libimobiledevice-1.3.0 precedent).
        conf = os.path.join(self.source_folder, "configure")
        replace_in_file(self, conf, "umask 077", "umask 022")

        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits the HMDFS jobserver fifo EPERM.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Tool-only package: drop the library, headers, pkg-config and man
        # trees installed by upstream's catch-all install rules
        # (libcpuid-tool convention).
        for leftover in ("lib", "include", "share", "sbin"):
            shutil.rmtree(os.path.join(self.package_folder, leftover),
                          ignore_errors=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
