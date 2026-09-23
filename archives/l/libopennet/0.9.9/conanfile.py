#!/usr/bin/env python3
"""Conan 2 recipe — libopennet 0.9.9 (Autotools: configure + make).

libopennet provides a stdio-like C API (fopen_net, fread_net, fseek_net,
...) that transparently opens local files AND http:// URLs, so programs
read remote resources exactly like local files.

Build system: legacy autoconf 2.59-era configure + handwritten Makefile.in
(no automake, no libtool).  The upstream Makefile always builds BOTH
libopennet.$(SHOBJEXT) (shared) and libopennet.$(AREXT) (static); the
`shared` option only selects what the downstream consumer links against.

Real installed artifacts (upstream `make install`):
    lib/libopennet.a
    lib/libopennet.so.0.9.9   (real ELF shared object)
    lib/libopennet.so.0       -> libopennet.so.0.9.9
    lib/libopennet.so         -> libopennet.so.0.9.9
    include/opennet.h
    man3/*.3                  (all but opennet.3 are 0-byte stubs; skipped)

Upstream bugs fixed by patch 0001 (required for any real consumer):
  1. fseek_net() calls ITSELF instead of fseeko_net() — infinite
     recursion / stack exhaustion on first fseek_net(..., SEEK_END).
  2. fopen_net() leaves `off_t length` uninitialized; open_net_internal()
     never writes *length for local-file paths, so stream->length becomes
     stack garbage propagating into flength_net().

Upstream test suite: `make test` builds test.c (a demo that prints file
contents via the library; it has NO assertions and no exit-code
semantics) — upstream formal test count: 0.  The recipe still compiles
and runs it offline as a smoke test (see build()); the real consumer
coverage lives in test_package/.

OHOS adaptations (knowledge-graph driven):
  E007  pass explicit --build/--host GNU triplets so the 2004-era
        config.guess (unaware of HarmonyOS) is never executed
  E114  patch 0002: drop `umask 077` from configure's confstat
        mktemp/mkdir lines (HMDFS forces setgid on dirs; a 0700 dir is
        unwritable by the build user, so config.status fails)
  E232  native OHOS build executor: run configure via /system/bin/sh
  E074  make -j1 (HMDFS jobserver fifo EPERM)
  E274  inject -Wl,-soname,libopennet.so.0 via LDFLAGS (upstream
        SHOBJLDFLAGS has no -soname; unversioned SONAME breaks the
        versioned symlink layout make install creates)

R26: default_options shared=False (system-name library).
R32: settings.os restricted to Linux/OHOS (BSD sockets).
R34: test_package exercises the real public API.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (get, apply_conandata_patches,
                               export_conandata_patches, copy)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibopennetConan(ConanFile):
    name = "libopennet"
    version = "0.9.9"
    description = "stdio-like C library for transparently opening local files and http:// URLs"
    license = "LGPL-2.1-or-later"  # opennet.c/opennet.h; net.c is GPL-2.0-or-later
    homepage = "https://www.rkeene.org/oss/libopennet/"
    url = ""  # filled by CI
    topics = ("http", "socket", "stdio", "network", "file")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # pure libc/POSIX socket API, zero external dependencies

    def validate(self):
        # R32
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libopennet requires BSD sockets: Linux/OHOS only, not "
                + str(self.settings.os)
            )

    def layout(self):
        # In-source build required: the handwritten Makefile.in pattern
        # rule `%_shr.o: %.c` has no VPATH support, so out-of-source make
        # fails with "No rule to make target 'opennet_shr.o'".  Same
        # approach as the adjtimex recipe.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # patch 0001 = upstream fseek_net/length bugs
        # patch 0002 = E114 (HMDFS umask 077 mktemp fix)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--prefix={self.package_folder}")
        # E274: upstream SHOBJLDFLAGS ("-shared -rdynamic") carries no
        # -soname; without one the linker records "libopennet.so" as the
        # NEEDED entry, which breaks the versioned layout (so.0.9.9 real
        # file + so.0 soname symlink) that make install creates.  LDFLAGS
        # is present in the Makefile.in .so link line, so inject here.
        if self.options.shared:
            tc.ldflags.append("-Wl,-soname,libopennet.so.0")
        # E007: the 2004-era config.guess does not recognize HarmonyOS.
        # Explicit --build/--host bypasses the probe; configure never
        # runs target binaries (all probes are AC_TRY_LINK compile-only).
        if str(self.settings_build.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        if str(self.settings_build.os) == "OHOS":
            self._configure_ohos()
        else:
            Autotools(self).configure()
        # E074: HMDFS jobserver fifo EPERM -> single-job make.
        # E274: the Makefile's `LDFLAGS = @LDFLAGS@` was expanded empty by
        # configure (env LDFLAGS only reaches the .so link line via a
        # command-line override), so force the -soname there.
        make_args = ["-j1"]
        if self.options.shared:
            make_args.append(
                "LDFLAGS=-Wl,-soname,libopennet.so.0")
        autotools = Autotools(self)
        autotools.make(args=make_args)
        self._run_upstream_test_smoke()

    def _configure_ohos(self):
        """E232: drive configure with the OHOS system shell on the native
        OHOS build executor, keeping Conan's full configure arg string."""
        autotools = Autotools(self)
        configure = os.path.join(self.source_folder, "configure")
        rc = self.run(
            f'CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh '
            f'/system/bin/sh "{configure}" {autotools._configure_args}',
            env="conanbuild",
            ignore_errors=True,
        )
        if rc != 0:
            config_log = os.path.join(self.build_folder, "config.log")
            if os.path.isfile(config_log):
                self.output.info("---- configure failed: config.log tail ----")
                try:
                    with open(config_log, "r", encoding="utf-8",
                              errors="replace") as fh:
                        self.output.info(fh.read()[-16000:])
                except OSError as exc:
                    self.output.info(f"(unreadable: {exc})")
            raise ConanException(
                f"native OHOS configure failed (exit {rc}); "
                "config.log tail echoed above"
            )

    def _run_upstream_test_smoke(self):
        """Compile and run the upstream `make test` driver (test.c) with an
        explicit argv[1] — upstream test.c dereferences argv[1] without
        checking, so running it bare crashes.  test.c is a demo (prints the
        given file's contents through the library), not an assertion suite;
        real consumer coverage is test_package/.  Offline: reads a local
        source file, no network involved."""
        cc = os.environ.get("CC", "cc")
        if not cc or shutil.which(shlex.split(cc)[0]) is None:
            cc = "clang"
        # Link the freshly built static archive explicitly: `-L. -lopennet`
        # would pick libopennet.so and then fail to relocate at run time
        # (no rpath in this ad-hoc smoke binary).
        self.run(
            f"{shlex.quote(cc)} -o test_upstream test.c "
            f"-I{shlex.quote(self.source_folder)} "
            f"{shlex.quote(os.path.join(self.build_folder, 'libopennet.a'))}",
            cwd=self.build_folder,
        )
        self.run(
            "./test_upstream "
            + shlex.quote(os.path.join(self.source_folder, "net.c")),
            cwd=self.build_folder,
        )

    def package(self):
        if str(self.settings_build.os) == "OHOS":
            self._package_ohos()
        else:
            Autotools(self).install(args=["-j1"])

    def _package_ohos(self):
        """E232-style manual install mirroring upstream `make install`
        exactly (install-sh is not executable on HMDFS).  man3 pages are
        skipped: every *.3 in the 0.9.9 tarball except opennet.3 is a
        0-byte stub."""
        bld = self.build_folder
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")
        # static lib is always produced by the upstream Makefile
        copy(self, "libopennet.a", src=bld, dst=lib_dir)
        if self.options.shared:
            # upstream install renames the unversioned build output
            # libopennet.so -> libopennet.so.0.9.9, then creates the
            # soname/dev symlinks; mirror that exactly (E274 layout)
            copy(self, "libopennet.so", src=bld, dst=lib_dir,
                 keep_path=False)
            built = os.path.join(lib_dir, "libopennet.so")
            real = os.path.join(lib_dir, "libopennet.so.0.9.9")
            if os.path.exists(built) and not os.path.exists(real):
                os.rename(built, real)
            os.symlink("libopennet.so.0.9.9",
                       os.path.join(lib_dir, "libopennet.so.0"))
            os.symlink("libopennet.so.0.9.9",
                       os.path.join(lib_dir, "libopennet.so"))
        copy(self, "opennet.h", src=bld, dst=inc_dir)

    def package_info(self):
        self.cpp_info.libs = ["opennet"]
