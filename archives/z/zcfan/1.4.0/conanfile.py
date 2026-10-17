#!/usr/bin/env python3
"""Conan recipe for zcfan 1.4.0 — zero-configuration ThinkPad fan daemon.

zcfan is a single-translation-unit C99 userspace daemon (zcfan.c, 388 lines)
that reads the temperature sensors exposed by the kernel hwmon class
(/sys/class/hwmon/hwmon*/temp*_input) and drives the ThinkPad ACPI fan
interface (/proc/acpi/ibm/fan) between the "off"/"low"/"medium"/"maximum"
levels, re-pinging the kernel watchdog and re-writing the level after resume.

Adaptation notes (HarmonyOS PC, aarch64):
    * Zero third-party dependencies — the only includes are <errno.h>,
      <glob.h>, <inttypes.h>, <limits.h>, <signal.h>, <stdio.h>, <stdlib.h>,
      <string.h>, <time.h>, <unistd.h>, i.e. pure libc/POSIX from the OHOS
      musl sysroot.  requirements() is therefore intentionally empty and no
      dependency-injection prefix is involved (R49 N/A).
    * Upstream is a hand-written Makefile project (no configure, no CMake).
      Its CFLAGS is a `:=` assignment that *appends* the environment CFLAGS,
      so only CC is injected on the make command line; the upstream
      `-std=gnu99 -O2 -pedantic -Wall -Wextra -Wwrite-strings -Warray-bounds
      -Wconversion -Wstrict-prototypes -Werror` set is preserved verbatim.
      The compiler path comes from Conan conf
      `tools.build:compiler_executables`, never from a bare shell variable
      (R33).
    * One portability patch: upstream `info()`/`err()` are variadic macros
      using the GNU `##__VA_ARGS__` token-paste extension.  GCC accepts it
      silently, clang's -pedantic (implied by upstream's own flag set, and
      -Werror turns it fatal) rejects it:

          zcfan.c:26:51: error: token pasting of ',' and __VA_ARGS__ is a
          GNU extension [-Werror,-Wgnu-zero-variadic-macro-arguments]

      Upstream never noticed because its CI only runs `make lint`,
      `make clean clang-tidy` and `make clean clang-everything` (verbatim from
      .github/workflows/ci.yml) — the latter explicitly
      passes -Wno-gnu-zero-variadic-macro-arguments, and plain `make` is
      never run with clang.  patches/0001-zcfan.c.patch rewrites the two
      macros to a pedantic-clean standard C99 form (`#define err(...)
      fprintf(stderr, "[ERR] " __VA_ARGS__)`) which keeps every call site
      unchanged.  No platform macro is introduced and the emitted text is
      byte-identical.
    * Upstream `make install` hardcodes the build-time $(bindir) into the
      generated systemd unit (`ExecStart=@bindir@/zcfan` sed-expanded at build
      time) and installs it to $(prefix)/lib/systemd/system/.  Packaging
      therefore copies the real artifacts directly instead of running the
      install target: bin/zcfan, share/man/man1/zcfan.1 and licenses/LICENSE.
      The systemd unit is upstream's Linux init integration and is not
      meaningful on HarmonyOS (no systemd), and shipping it would bake a
      Conan cache path into a shipped file.
    * Runtime contract: with no argument the daemon requires the ThinkPad
      ACPI fan interface (/proc/acpi/ibm/fan).  On a host without
      thinkpad_acpi it aborts by design (upstream `expect(f)`), exactly as it
      does on a non-ThinkPad Linux machine — see the consumer tests for the
      asserted behaviour.  Running it with any argument prints the usage
      banner and exits 0 without touching the hardware.

Artifacts: bin/zcfan (+ share/man/man1/zcfan.1); the CLI is declared in the
software-level commands.json (R38).
License: MIT.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZcfanConan(ConanFile):
    name = "zcfan"
    version = "1.4.0"
    description = "Zero-configuration fan daemon for ThinkPads"
    license = "MIT"
    homepage = "https://github.com/cdown/zcfan"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("fan", "thermal", "thinkpad", "daemon", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        """Intentionally empty: zcfan links nothing but libc (see module docstring)."""

    def layout(self):
        basic_layout(self)
        # Plain hand-written Makefile project: build in the source folder.
        self.folders.build = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException("zcfan requires a POSIX host (Linux or OHOS)")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: -j1.  Only CC is injected: upstream's CFLAGS is a `:=` assignment
        # that appends $(CFLAGS), so a command-line CFLAGS would *replace* the
        # upstream -pedantic -Werror set instead of extending it.  Passing the
        # toolchain CFLAGS is unnecessary here — the OHOS clang at the profile's
        # compiler path already targets aarch64-linux-ohos with the musl sysroot.
        self.run('make -j1 CC="{0}"'.format(cc))

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        licdir = os.path.join(self.package_folder, "licenses")
        for d in (bindir, mandir, licdir):
            os.makedirs(d, exist_ok=True)

        copy(self, "zcfan", src=self.source_folder, dst=bindir, keep_path=False)
        copy(self, "zcfan.1", src=self.source_folder, dst=mandir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=licdir, keep_path=False)

        exe = os.path.join(bindir, "zcfan")
        if not os.path.isfile(exe):
            raise ConanException("package(): missing build artifact %s" % exe)
        os.chmod(exe, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
