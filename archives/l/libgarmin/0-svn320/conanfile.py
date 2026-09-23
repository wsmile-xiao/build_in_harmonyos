#!/usr/bin/env python3
"""Conan recipe — libgarmin 0-svn320 (Garmin IMG parser, static library).

libgarmin parses Garmin IMG files used by Garmin GPS devices.  Upstream only
publishes an SVN snapshot (Debian repackages it as `libgarmin_0~svn320.orig.tar.gz`
at SVN r320); the tarball does not contain a pre-generated `configure`, so the
autotools tree would require `autoreconf`/`automake`, which are not available in
the OHOS build environment.  We therefore build the static library directly with
the OHOS clang:

  * a minimal ``src/config.h`` — the source code does not consume any ``HAVE_*``
    macros, so a thin header pulling in the standard C types/functions is enough;
  * ``-DDEBUG`` — upstream ``configure.ac`` enables this by default, and several
    struct members (``struct gpoint``/``struct gpoly``) are guarded by
    ``#ifdef DEBUG``;
  * ``-include config.h`` — force every translation unit to see ``NULL`` /
    standard types (a couple of files rely on transitive includes that differ on
    OHOS);
  * a small hand-written ``src/Makefile`` that compiles the sources into
    ``libgarmin.a``.

No source-level patches are needed; the package is a static-only library, so it
ships no executable and needs no ``commands.json`` (R38).
"""
import os
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgarminConan(ConanFile):
    name = "libgarmin"
    version = "0-svn320"
    description = "Library to parse Garmin IMG files as used by Garmin GPS devices"
    license = "GPL-2.0-only"
    homepage = "https://libgarmin.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("garmin", "gps", "img", "geospatial")

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libgarmin supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The SVN snapshot ships config.h.in but no generated config.h, and
        # garmin.c unconditionally includes "version.h" (normally produced from
        # the .svn working copy).  Provide both so the build needs no autoreconf.
        src = os.path.join(self.source_folder, "src")
        with open(os.path.join(src, "config.h"), "w") as fh:
            fh.write(
                "#ifndef LIBGARMIN_CONFIG_H\n"
                "#define LIBGARMIN_CONFIG_H\n"
                "#include <sys/types.h>\n"
                "#include <stdint.h>\n"
                "#include <stdlib.h>\n"
                "#include <string.h>\n"
                "#include <stdio.h>\n"
                "#include <unistd.h>\n"
                "#include <fcntl.h>\n"
                "#endif\n"
            )
        with open(os.path.join(src, "version.h"), "w") as fh:
            fh.write(
                "#ifndef LIBGARMIN_VERSION_H\n"
                "#define LIBGARMIN_VERSION_H\n"
                '#define LIBVERSION "libgarmin 0.1-r320"\n'
                '#define PACKAGE_VERSION "0.1-r320"\n'
                "#endif\n"
            )
        # Hand-written Makefile: build the static library with the OHOS clang.
        # CC/AR are pinned to absolute paths so a leaked CC=cc in the environment
        # cannot break the build, and the flag set is self-contained (it ignores
        # any CFLAGS injected by the surrounding environment).
        with open(os.path.join(src, "Makefile"), "w") as fh:
            fh.write(
                "CC = /data/service/hnp/bin/clang\n"
                "AR = /data/service/hnp/bin/llvm-ar\n"
                "OBJS = $(patsubst %.c,%.o,$(wildcard *.c))\n"
                "all: libgarmin.a\n"
                "libgarmin.a: $(OBJS)\n"
                "\t$(AR) rcs $@ $^\n"
                "%.o: %.c\n"
                "\t$(CC) -c $< -o $@ -I. -include config.h -fPIC -DDEBUG\n"
            )

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # Apply any conandata.yml / patches/-directory patches (no-op here since
        # patches_applied is empty, but required by conan-verify G1 + tooling).
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "src")
        # Build with subprocess directly (not conan's self.run): on OHOS,
        # self.run can silently drop the compiler's stderr (the "静默失败"
        # quirk), so a failing compile reports only "make: Error 1" with no
        # diagnostic.  Capturing output here surfaces the real error.  The
        # hand-written Makefile pins CC/AR to absolute paths and uses a fixed
        # flag set, so the build is self-contained and unaffected by any
        # CC=cc / CFLAGS leakage in the surrounding environment.
        cmd = "make -j1"
        last_diag = ""
        for attempt in range(3):
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=src, env=os.environ,
            )
            if r.stdout:
                print(r.stdout, end="")
            if r.stderr:
                print(r.stderr, end="", file=sys.stderr)
            if r.returncode == 0:
                return
            last_diag = (r.stderr or r.stdout or "").strip()
        raise ConanException(
            f"make failed after 3 attempts: {last_diag[:500]}"
        )

    def package(self):
        src = os.path.join(self.source_folder, "src")
        copy(self, "libgarmin.a", src=src, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libgarmin.h", src=src, dst=os.path.join(self.package_folder, "include"))
        copy(
            self,
            "garmintypes.txt",
            src=os.path.join(self.source_folder, "data"),
            dst=os.path.join(self.package_folder, "share", "libgarmin"),
        )
        # Generate libgarmin.pc (substitutes the original libgarmin.pc.in values).
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        with open(os.path.join(pc_dir, "libgarmin.pc"), "w") as fh:
            fh.write(
                f"prefix={self.package_folder}\n"
                "exec_prefix=${prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: libgarmin\n"
                "Description: Handle Garmin image files\n"
                f"Version: {self.version}\n"
                "Libs: -L${libdir} -lgarmin\n"
                "Cflags: -I${includedir}\n"
            )

    def package_info(self):
        self.cpp_info.libs = ["garmin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
