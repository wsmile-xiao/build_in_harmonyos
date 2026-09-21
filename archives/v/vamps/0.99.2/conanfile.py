#!/usr/bin/env python3
"""Conan recipe for vamps 0.99.2 — DVD-9 → DVD-5 MPEG-2 program-stream requantizer.

vamps evaporates DVD-compliant MPEG-2 program streams by selectively copying
audio and subpicture tracks and by re-quantizing the embedded elementary video
stream.  Upstream is a hand-written recursive Makefile project (no configure,
no CMake) shipping two command-line tools:

    * vamps      — the requantizer itself (vamps/vamps.c + requant.c);
                   links only -lm -lpthread (both stubs exist in the OHOS
                   SDK sysroot: usr/lib/aarch64-linux-ohos/lib{m,pthread}.a)
    * play_cell  — plays a single cell from a DVD device/backup; the only
                   consumer of libdvdread (LOADLIBES += -ldvdread; headers
                   <dvdread/ifo_read.h>, <dvdread/nav_read.h>)

Adaptation notes (HarmonyOS PC, aarch64):
    * No build-system patch needed.  The Makefile hardcodes `CC = gcc`, but CFLAGS is
      `?=` and LDFLAGS is `+=`, so command-line assignments win — build()
      injects CC/CFLAGS/LDFLAGS on the make command line (R33: compiler path
      from Conan conf `tools.build:compiler_executables`, never a bare shell
      variable).  Passing LDFLAGS explicitly also drops the upstream `-s`
      link-time strip, which is meaningless for relocatable packaging.
    * libdvdread/7.1.0 is consumed in its default *static* variant, so both
      tools end up as self-contained OHOS binaries (no SONAME-symlink runtime
      exposure, cf. E316/E492/E505).
    * Source is plain POSIX C: `_GNU_SOURCE` is defined in vamps.c so musl
      provides `getopt_long_only`; no linux/asm headers, no lseek64/mmap.
      One portability patch: requant.c relies on the legacy SysV `uint`
      typedef (glibc-only via <sys/types.h> __USE_MISC; absent in musl).
    * Upstream `install` target needs install(1) and bakes PREFIX paths —
      package() copies the two binaries + COPYING directly instead.
Artifacts: bin/vamps, bin/play_cell (software-level commands.json declares
the CLI, R38).
License: GPL-2.0-or-later.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class VampsConan(ConanFile):
    name = "vamps"
    version = "0.99.2"
    description = (
        "Tool to shrink DVD-compliant MPEG-2 program streams by selectively "
        "copying audio and subpicture tracks and re-quantizing the video stream"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/vamps/"
    url = "https://sourceforge.net/projects/vamps/"
    topics = ("dvd", "mpeg2", "requantizer", "video", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Plain hand-written Makefile project: build in the source folder.
        self.folders.build = "."

    def source(self):
        # URL ends in "/download" (SourceForge redirect endpoint): without an
        # explicit filename get() would deduce "download" and pick the wrong
        # decoder (abcmidi precedent).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="vamps-0.99.2.tar.gz")

    def requirements(self):
        # play_cell is the only libdvdread consumer (link + headers).
        # Default static variant keeps both tools self-contained.
        self.requires("libdvdread/7.1.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException("vamps requires a POSIX host (Linux or OHOS)")

    @staticmethod
    def _first_dir(dep, attr):
        """First cpp_info directory of a dependency, made absolute."""
        dirs = list(getattr(dep.cpp_info, attr, []) or [])
        if not dirs:
            return ""
        path = dirs[0]
        return path if os.path.isabs(path) else os.path.join(dep.package_folder, path)

    def generate(self):
        dvdread = self.dependencies["libdvdread"]
        self._dvdread_inc = self._first_dir(dvdread, "includedirs")
        self._dvdread_lib = self._first_dir(dvdread, "libdirs")
        if not self._dvdread_inc or not self._dvdread_lib:
            raise ConanException(
                "libdvdread package exposes no include/lib dirs — cannot wire play_cell"
            )
        # No generator files needed: the hand-written Makefile consumes flags
        # injected on the make command line in build().

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: -j1.  Command-line variables override the Makefile's `CC = gcc`
        # (plain assignment), satisfy `CFLAGS ?=` and suppress `LDFLAGS += -s`
        # (GNU make: command-line assignments beat makefile ones unless the
        # `override` directive is used).  LOADLIBES is untouched on purpose:
        #   vamps      → -lm -lpthread   (both stubs in OHOS SDK sysroot)
        #   play_cell  → -ldvdread       (static .a from the libdvdread package)
        self.run(
            'make -j1 CC="{0}" '
            'CFLAGS="-pipe -O2 -DHAVE_BUILTIN_EXPECT -I{1}" '
            'LDFLAGS="-L{2}"'.format(cc, self._dvdread_inc, self._dvdread_lib)
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        licdir = os.path.join(self.package_folder, "licenses")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(licdir, exist_ok=True)
        # Direct copy: upstream `make install` needs install(1) and hardcodes
        # PREFIX into the destination path.
        copy(self, "vamps", src=os.path.join(self.source_folder, "vamps"),
             dst=bindir, keep_path=False)
        copy(self, "play_cell", src=os.path.join(self.source_folder, "play_cell"),
             dst=bindir, keep_path=False)
        copy(self, "COPYING", src=self.source_folder, dst=licdir, keep_path=False)
        for exe in ("vamps", "play_cell"):
            path = os.path.join(bindir, exe)
            if not os.path.isfile(path):
                raise ConanException("package(): missing build artifact %s" % path)
            os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Application package: no libdvdread re-export (consumers of vamps do
        # not consume its headers or libraries).
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
