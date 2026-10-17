#!/usr/bin/env python3
"""Conan recipe — librecast 0.8.0 (Librecast IPv6 multicast library).

Upstream: https://codeberg.org/librecast/librecast (mirror: https://git.sr.ht/~librecast/librecast)
Autotools build. Upstream ships a hand-written src/Makefile.in that only
produces the shared object (`all: $(SOFILES)`), so `--enable-static` /
`--disable-shared` are not honoured and no static-linking args are passed.

Bundled sources: `libs/blake3` (BLAKE3 reference C implementation, built as a
static libblake3.a) and `libs/libmld` (MLDv2 listener, built via
AC_CONFIG_SUBDIRS and linked directly into liblibrecast.so).  Neither is a
separate Conan package.

Third-party libraries (both reach the public headers, hence public requires):
  - lcrq      — RaptorQ FEC; include/librecast/net.h includes <lcrq.h>
  - libsodium — encryption/hashing; include/librecast/crypto.h includes <sodium.h>

OHOS adaptations (see conandata.yml descriptions and notes.md):
  - E007 config.guess/config.sub: teach the bundled autotools helpers about
    HarmonyOS ("aarch64-unknown-linux-ohos"), including the kernel-os
    validation table entry `linux-ohos*` (top level and nested libmld).
  - E129/E114: configure and libs/libmld/configure create their temp dir with
    `umask 077 && mktemp -d`.  On setgid HMDFS mounts that yields drwx--S---
    and config.status aborts with "Permission denied" while writing subs1.awk.
    Both are switched to umask 022, which is the fix used by other autotools
    archives here.
  - E091: libs/libmld/src/mld.c includes <linux/netlink.h>, whose kernel UAPI
    copy of struct sockaddr_storage collides with musl's <sys/socket.h>.
    Renamed around those includes under `#ifndef __GLIBC__`.
  - uname: OHOS reports "HarmonyOS" from uname -s, so src/Makefile's
    `ifeq ($(OSNAME),Linux)` was false and the wrong interface implementation
    was selected (if.o, which lacks lc_tuntap_create).  Makefile.in normalises
    HarmonyOS to Linux.
  - E127 pthread_cancel: musl has no working thread cancellation (the device
    libc exports pthread_cancel but it returns ENOSYS, and pthread_setcanceltype
    is absent, so the shared object cannot even be relocated).  The library's
    thread teardown is rewritten to cooperative shutdown: a NULL-function stop
    sentinel for the smolq/mld job queues, a stop flag plus shutdown() for the
    listen thread, a stop flag for the NACK logger and MDL timer, and closure of
    the netlink/listen sockets to release the blocking recvmsg().
  - RFC 3542 inet6_opt_*: musl does not implement the hop-by-hop/destination
    option builders that libs/libmld/src/mld.c calls unconditionally, so
    liblibrecast.so fails to relocate at load time on OHOS.  A conforming
    implementation (same bytes as glibc/FreeBSD, transcribed from the KAME
    reference) is compiled in under `#if defined(__linux__) && !defined(__GLIBC__)`.

Platform macros appear only in patches/ guarded by libc-capability or
`__linux__ && !__GLIBC__` conditions, never as an `#ifdef __OHOS__` stub.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class LibrecastConan(ConanFile):
    name = "librecast"
    version = "0.8.0"
    description = ("Librecast — fast, efficient and scalable communication by "
                   "leveraging IPv6 multicast (IPv6 multicast library)")
    license = "GPL-2.0-only OR GPL-3.0-only"
    homepage = "https://librecast.net/librecast.html"
    url = "https://codeberg.org/librecast/librecast"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Both headers are pulled in by librecast's own public headers
        # (net.h -> <lcrq.h>, crypto.h -> <sodium.h>), so they are public
        # requirements rather than implementation details.
        self.requires("lcrq/0.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("libsodium/1.0.22", transitive_headers=True, transitive_libs=True)

    def layout(self):
        # librecast's hand-written Makefiles are in-source only: `make -C src`
        # expects the .c files in the current tree (no VPATH), and
        # src/Makefile links ../libs/libmld/src/*.o by relative path, so the
        # build folder must be the source folder.
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps feeds each requirement's -I / -L / -l (and RPATH) into
        # CPPFLAGS/LDFLAGS/LIBS.  Without it configure cannot resolve the
        # AC_CHECK_LIB(lcrq)/AC_CHECK_LIB(sodium) probes and silently disables
        # both features (HAVE_LIBLCRQ / HAVE_LIBSODIUM undef), which then fails
        # to compile (librecast_pvt.h needs <lcrq.h>) and would ship a library
        # with FEC and encryption compiled out.
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        # In-source build (see layout()): srcdir is "." by construction.  State
        # it explicitly because configure otherwise forks `expr`/`sed` to
        # auto-detect srcdir and aborts with "cannot find sources (src/) in  or
        # .." whenever such a fork fails (seen on memory-constrained workers).
        tc.configure_args.append("--srcdir=.")
        # Upstream only builds the shared object (Makefile.in `all: $(SOFILES)`);
        # --enable-static/--disable-shared are not honoured by its hand-written
        # Makefiles, so those flags are deliberately not passed here.
        tc.generate()

        # configure compiles and *runs* conftest programs (AC_CHECK_LIB(lcrq),
        # AC_CHECK_LIB(sodium), "cannot run C compiled programs").  The OHOS
        # loader has no default search path for conan-cached shared libraries,
        # and lcrq is shared-only, so the probes fail with
        # "Error loading shared library liblcrq.so.0.0" unless LD_LIBRARY_PATH
        # points at the dependency lib dirs while configure runs.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["librecast"]
        # Public headers include <lcrq.h> and <sodium.h>, so consumers need
        # both to compile.
        self.cpp_info.requires = ["lcrq::lcrq", "libsodium::libsodium"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m", "dl"]
