#!/usr/bin/env python3
"""Conan recipe for smp-utils 0.99 — SAS Management Protocol utilities.

smp-utils is Douglas Gilbert's SMP tool suite from the sg3_utils family.
It builds the libsmputils1 library plus 29 smp_* command-line tools
(REPORT GENERAL, DISCOVER, PHY CONTROL, zoning, GPIO, ...).

OHOS adaptations (all without patch files):
    - The upstream site is unreachable from this network, so the source
      tarball is taken from the Debian pool mirror (same approach as
      a52dec / plink / spaced); the archive ships pre-generated configure
      and Makefile.in, so no autoreconf and no automake/libtool
      tool_requires are needed.
    - Host detection: the bundled 2018 config.sub accepts
      aarch64-unknown-linux-gnu but not aarch64-unknown-linux-ohos, and
      CI workers report HarmonyOS via uname which old config.guess cannot
      map. Passing --build/--host explicitly (build == host, a52dec mode)
      keeps configure in native mode and avoids config.guess entirely.
    - E114: generated configure uses `umask 077 && mktemp` for its
      config.status temp dir; on HMDFS that dir ends up unwritable.
      Relax umask 077 -> 022 before configure.
    - Static linkage requested by default (R26-friendly, qemu-friendly):
      -static is appended to LDFLAGS for static builds and shared libs
      are disabled.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SmpUtilsConan(ConanFile):
    name = "smp-utils"
    version = "0.99"
    description = (
        "SAS Management Protocol (SMP) utilities from the sg3_utils "
        "family: libsmputils1 plus 29 smp_* command-line tools."
    )
    license = "BSD-3-Clause"
    homepage = "https://sg.danny.cz/sg/smp-utils.html"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is only supported on Linux/OHOS, not {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Bundled config.sub (2018) accepts aarch64-unknown-linux-gnu;
            # native mode (build == host) skips config.guess, which cannot
            # map HarmonyOS uname output on CI workers (E007). Same as a52dec.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        if not self.options.shared:
            # R26-friendly fully static artifacts (qemu-direct, no RPATH).
            # configure still sees a plain -static (valid clang flag); the
            # libtool -all-static needed for the final link is injected as a
            # make command-line override in build() because libtool swallows
            # a bare -static found in LDFLAGS (verified: bins came out as
            # dynamic PIE without it).
            tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            # E114: HMDFS + umask 077 -> unwritable config.status temp dir.
            replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)
        # musl compatibility: lib/mpi_type.h names the glibc-only type
        # u_int32_t; the fixed-width uint32_t from the same stdint family
        # already used next to it (int32_t) is the portable spelling.
        mpi_type_path = os.path.join(self.source_folder, "lib", "mpi_type.h")
        if os.path.isfile(mpi_type_path):
            replace_in_file(self, mpi_type_path, "u_int32_t", "uint32_t", strict=False)
        # chk_aac_device fopen(/proc/devices) returns NULL on OHOS (no
        # /proc/devices); upstream only guards the fprintf with verbose,
        # so verbose=0 falls through to fgets(NULL) -> SIGABRT (exit 134).
        # Fix the guard to always return on NULL fp.
        aac_io_path = os.path.join(self.source_folder, "lib", "smp_aac_io.c")
        if os.path.isfile(aac_io_path):
            replace_in_file(self, aac_io_path, "if(NULL == fp && verbose)", "if(NULL == fp)", strict=False)
        static_make_args = None if self.options.shared else ["LDFLAGS='-static -all-static'"]
        autotools = Autotools(self)
        autotools.configure()
        # Command-line make variables override the Makefile value and
        # propagate to sub-makes: -static reaches non-libtool links and
        # -all-static makes libtool pass -static to the real linker.
        # Shell-quoted so make receives one "LDFLAGS=..." assignment
        # (a bare -all-static word would be eaten as a make option).
        #
        # The override must be repeated on EVERY make invocation, not just the
        # first one: automake's `check` re-runs `all` and re-links the library
        # and all 29 programs, and that re-link does not inherit a command-line
        # variable from the previous make process. Without -all-static libtool
        # swallows the bare -static still present in LDFLAGS and silently
        # produces dynamic PIE binaries. Verified with a clean local gate:
        # 58 link lines = 29 with -all-static + 29 without, the installed
        # smp_rep_general came out `pie executable ... dynamically linked`
        # with NEEDED libc.so, and test_package's static assertion failed.
        autotools.make(args=static_make_args)
        # Upstream ships no test suite (no TESTS= in any Makefile.am), so
        # automake's default `make check` is a no-op; still run it for the
        # record (T009) — it must exit 0. The LDFLAGS override is repeated so
        # the re-link triggered by `check` stays static.
        autotools.make(target="check", args=static_make_args)

    def package(self):
        static_make_args = None if self.options.shared else ["LDFLAGS='-static -all-static'"]
        autotools = Autotools(self)
        autotools.install(args=static_make_args)
        # Remove libtool *.la wrappers (Conan 2 copy() has no delete=).
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["smputils1"]
        self.cpp_info.includedirs = ["include", "include/scsi"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
