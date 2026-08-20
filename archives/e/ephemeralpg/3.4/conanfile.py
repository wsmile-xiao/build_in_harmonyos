#!/usr/bin/env python3
"""Conan recipe for ephemeralpg 3.4 (upstream Makefile build).

OHOS adaptation notes:
- Minimal Makefile package producing two artifacts:
  * getsocket — C program (getsocket.c) that fetches an unused TCP port via
    standard POSIX socket/bind/getsockname API. Fully OHOS-compatible, no patch.
  * pg_tmp   — shell script generated from pg_tmp.sh via sed version substitution.
- No Conan link dependencies; PostgreSQL is a *runtime* dependency only
  (requirements() is empty).
- Build uses `make` with CC/CFLAGS taken from the OHOS profile via
  `tools.build:compiler_executables` (R33: never rely on shell env vars).
- STRIP=true is passed to both `make` and `make install`: the upstream install
  target strips the installed binary by default, and the OHOS MAC kernel
  rejects stripped binaries (Operation not permitted). Keeping it unstripped
  matches the abduco 0.6 adaptation pattern.
- getsocket.c uses only POSIX socket APIs, no OHOS-specific patch required.
- pg_tmp.sh internally uses ${SYSTMP:-/tmp} for its temp directory; no source
  modification needed (the recipe does not hard-code /tmp).
"""

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class EphemeralpgConan(ConanFile):
    name = "ephemeralpg"
    version = "3.4"
    description = "Run tests on an isolated, temporary PostgreSQL database."
    license = "ISC"
    homepage = "https://github.com/eradman/ephemeralpg"
    url = "https://github.com/eradman/ephemeralpg"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan link dependencies; PostgreSQL is a runtime-only dependency.
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("ephemeralpg requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # STRIP=true: upstream `make` invokes strip on the produced binary;
        # OHOS MAC rejects stripped binaries, so skip stripping (abduco pattern).
        strip = "true"
        self.run(
            "make -j1 CC={} STRIP={} PREFIX=/usr MANPREFIX=/usr/share/man".format(
                cc, strip
            )
        )

    def package(self):
        # Empty PREFIX installs directly under the Conan package root.
        # Pass STRIP=true again: upstream `make install` strips the installed
        # binary by default, and on OpenHarmony the kernel MAC rejects stripped
        # binaries (Operation not permitted) — keep it unstripped (see build()).
        self.run(
            "make install PREFIX= MANPREFIX=share/man STRIP=true DESTDIR={}".format(
                self.package_folder
            )
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
