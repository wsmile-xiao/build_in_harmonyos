#!/usr/bin/env python3
"""Conan recipe — rtl-wmbus 1.1.0

Wireless M-Bus software-defined receiver (https://github.com/wmbusmeters/rtl-wmbus).

Build system: plain Makefile, single translation unit (`rtl_wmbus.c` includes all
signal-chain headers), no configure script.

The upstream README lists "RTL-SDR library" as a requirement, but that is a
*runtime* peer process (`rtl_sdr ... | rtl_wmbus`), not a link dependency: the
Makefile links only `-lm`. The recipe therefore declares no `requires`.

Version banner
--------------
The upstream Makefile derives its banner from git:

    TAG?=$(shell git describe --tags --always)
    BRANCH?=$(shell git rev-parse --abbrev-ref HEAD)
    ifeq ($(BRANCH),master)
      BRANCH:=
    else
      BRANCH:=$(BRANCH)_
    endif
    VERSION:=$(BRANCH)$(TAG)

A Conan source folder has no `.git`, so the three values are injected into the
**build environment** (via `GnuToolchain(self).extra_env`, which writes the
conanbuild env file that `self.run()` sources). Make gives *command-line*
assignments priority over makefile assignments while treating environment
variables as defaults — so the `?=` lines keep our values and the `ifeq` above
still fires and clears BRANCH, reproducing exactly the banner a tagged `master`
checkout would produce (`1.1.0`). Passing the same values on the `make` command
line instead would defeat the `BRANCH:=` rewrite and yield `master1.1.0`.

Build-time `build/version.h`
---------------------------
`rtl_wmbus.c` does `#include "build/version.h"`, and the Makefile generates that
file at *parse* time through a chain of `$(shell ...)` calls (mkdir / echo / cat -n
/ mv) that also derive the banner from git. Two things break on a CI worker:

  * the source tree has no `.git` (see above), and
  * the worker's minimal PATH may not provide the coreutils those `$(shell)`
    calls need. The CI log for PR #14175 shows the same signature in the
    pre-download step (`[Errno 2] No such file or directory` for the download
    tool the worker had no PATH entry for).

When `cat -n` cannot read the freshly written `.tmp`, `PREV_VERSION` and
`CURR_VERSION` both come back empty, so the Makefile's `ifneq` is false and it
takes the `rm` branch — leaving `build/version.h` absent and the build failing
with `fatal error: 'build/version.h' file not found`.

`build()` therefore writes `build/version.h` itself, byte-identical to what the
Makefile emits when its own generation works. No upstream source is patched and
`make` is still the build system.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class RtlWmbusConan(ConanFile):
    name = "rtl-wmbus"
    version = "1.1.0"
    description = ("Wireless M-Bus (868 MHz) software-defined receiver: reads raw "
                   "RTL-SDR IQ samples on stdin, decodes T1/C1/S1 telegrams to stdout")
    # Upstream tag 1.1.0 (34684e655df70867ac86e799561ec6512c45be0a) is BSD-2-Clause:
    # its README "License" section carries "Copyright (c) 2024 <xael.south@yandex.com>"
    # followed by the verbatim two-clause BSD terms, and debian/copyright records
    # `Files: *` -> `License: BSD-2-Clause`. The tarball mentions GPL nowhere.
    license = "BSD-2-Clause"
    homepage = "https://github.com/wmbusmeters/rtl-wmbus"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS must be listed alongside Linux, never compared with `==`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rtl-wmbus supports Linux/OHOS only, got {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "OHOS builds require arch=armv8 (aarch64)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        # See module docstring. Conan >=2.29 exposes `tc.extra_env` (not the
        # older `tc.vars`); these land in the build-scope conanbuild env file,
        # which self.run() sources automatically.
        tc.extra_env.define("BRANCH", "master")
        tc.extra_env.define("TAG", self.version)
        tc.extra_env.define("COMMIT_HASH", self.conan_data["commit"])
        tc.extra_env.define("CHANGES", "")
        tc.generate()

    def build(self):
        # R33: compiler comes from Conan conf, never from a bare ${CC} shell var
        # (release workers have an empty environment — it would fail silently).
        # CC is a plain `CC=gcc` assignment in the Makefile, so an inherited
        # value would be shadowed: it must be overridden on the command line.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={},
                                   check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # ---- pre-create build/version.h (see module docstring) -------------
        # The Makefile derives it from git at *parse* time via $(shell ...) and
        # only renames the .tmp into place when the .tmp is readable. On a CI
        # worker whose minimal PATH cannot provide the required coreutils the
        # `cat -n` probes come back empty, PREV_VERSION == CURR_VERSION, and the
        # Makefile takes the `rm` branch — so build/version.h is never created
        # and the build dies with `fatal error: 'build/version.h' file not found`.
        #
        # Writing the file here removes that dependency. The bytes below are
        # byte-identical to what the Makefile emits when its own generation
        # does work, so on a fully functional toolchain the Makefile compares
        # the two as equal and takes its `rm` branch, leaving ours in place.
        build_dir = os.path.join(self.source_folder, "build")
        os.makedirs(build_dir, exist_ok=True)
        with open(os.path.join(build_dir, "version.h"), "w", encoding="utf-8") as fh:
            fh.write(f'#define VERSION "{self.version}"\n')
            fh.write(f'#define COMMIT "{self.conan_data["commit"]}"\n')

        # R9: -j1 — single translation unit, nothing to parallelise anyway.
        self.run(f'make release CC="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        copy(self, "rtl_wmbus", src=os.path.join(self.source_folder, "build"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
