#!/usr/bin/env python3
"""Conan recipe for ttygif 1.5.0 — replay a ttyrec recording into an animated GIF.

ttygif 1.5.0 is the **C** implementation (the later upstream rewrite is Go).  It
reads an ttyrec recording, replays it into the terminal, snapshots the terminal
window once per frame with `xwd -id $WINDOWID -out <scratch>/<n>.xwd`, and then
stitches the frames with
`convert -loop 0 -delay <1/100 s> … -layers Optimize tty.gif`.
Upstream is a hand-written bare Makefile project: no configure, no CMake, four
C translation units (ttygif.c / io.c / string_builder.c / utils.c) and zero
third-party libraries.

HarmonyOS PC adaptation (this recipe + patches/):

  * Headless usability (patch 0001, two hunks in ttygif.c):
      - Frame scratch directory.  Upstream hardcoded the mkdtemp() template
        "/tmp/ttygif.XXXXXX".  On HarmonyOS PC /tmp sits on a read-only mount
        (measured: `touch /tmp/x` -> "Read-only file system"), so mkdtemp()
        always failed and main() aborted in its very first statements.
        The template now takes its root from TMPDIR (the POSIX override, and
        the remedy recorded as E002) and keeps /tmp as the fallback when TMPDIR
        is unset, which leaves Linux/macOS behaviour unchanged.
      - `--help` / `--version` are handled before any display-related setup.
        Previously the WINDOWID lookup and mkdtemp() ran first, so a packaged
        `ttygif --version` could exit non-zero purely because no X window or
        writable /tmp was around — which also makes CI's L2 smoke probe and any
        "is it installed?" check unreliable.
  * Version string (patch 0002).  Tag 1.5.0 still ships `VERSION = '"1.4.0"'`,
    i.e. the binary self-reported a version that does not exist upstream; it is
    aligned with the tag (and with this package's own version).
  * Toolchain.  `CC = gcc` is a *plain* makefile assignment, so the ambient $CC
    is silently ignored; build() overrides it on the make command line (GNU
    make: command-line variables beat makefile ones) with the compiler taken
    from Conan's `tools.build:compiler_executables` conf — never from a bare
    shell variable (R33).  CFLAGS is deliberately NOT passed: the Makefile's
    `CFLAGS += -O2 -Wall -DVERSION=$(VERSION)` is dropped wholesale the moment a
    command-line CFLAGS exists, which would silently remove -DVERSION.
  * Install.  `make install` is not used at all: it bakes the default PREFIX
    into the rule and `install -m755` relies on chmod behaviour HMDFS normalises
    away (E046, the M18 "烧路径" family).  package() copies the artifacts.
  * Runtime tools.  ttygif shells out to ImageMagick's `convert`, so that is a
    *run* requirement, not a link one:
    `requires("imagemagick/7.1.2.29", headers=False, libs=False, run=True)`.
    tool_requires / run=False never reach the conanrun environment (E365/E442;
    in-repo shape: datefudge→coreutils, fcheck→perl, alive→guile).
    The capture side shells out to `xwd`, which is **not** a published Conan
    package: archives/x/xwd/1.0.9 carries only manifest/notes/patches (no
    conanfile.py) and `conan download xwd --only-recipe` against the published registry ->
    "Recipe 'xwd' not found".  R36/PF4 forbid adapting a dependency inside this
    PR, so xwd stays an externally-provided command (documented in README.md)
    and the on-screen capture path is disclosed as an unexecuted test item with
    measured evidence rather than stubbed into a pass.
  * Consumers of this package must additionally have `convert` reachable on
    PATH.  The published imagemagick recipe declares components only (no
    cpp_info.bindirs), so VirtualRunEnv does not export its bin/ — measured in
    this task: `conan install --requires=imagemagick/7.1.2.29
    -g VirtualRunEnv` produced a conanrun.sh whose PATH contained libpng's
    bindir only.  test_package resolves the directory explicitly instead of
    baking another package's absolute cache path into this one's env_info.

Artifacts: bin/ttygif, licenses/LICENSE (the software-level commands.json
declares the CLI, R38).
License: MIT (upstream LICENSE); io.c/ttygif.c additionally carry the older
BSD-4-clause ttyrec copyright, noted in README.md.
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


class TtygifConan(ConanFile):
    name = "ttygif"
    version = "1.5.0"
    description = (
        "Replays a ttyrec terminal recording and exports it as an animated GIF, "
        "snapshotting the window with xwd and stitching the frames with "
        "ImageMagick"
    )
    license = "MIT"
    homepage = "https://github.com/icholy/ttygif"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("ttyrec", "gif", "terminal", "screenshot", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Bare Makefile with no VPATH: the objects and the binary land next to
        # the sources, so the build tree *is* the source tree.
        self.folders.build = "."

    def source(self):
        # The codeload URL ends with the bare tag name ("…/refs/tags/1.5.0"),
        # which carries no extension, so get() has to be told the archive name
        # or it picks the wrong decompressor (same trap as archives/v/vamps
        # with SourceForge's "/download" tail).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="ttygif-1.5.0.tar.gz")

    def requirements(self):
        # ttygif links nothing, but calls `convert` through system()/popen() to
        # assemble the GIF: a run-time requirement, hence run=True with
        # headers/libs switched off.
        self.requires("imagemagick/7.1.2.29",
                      headers=False, libs=False, run=True)

    def validate(self):
        # R32: a platform test has to accept the OHOS enum next to Linux.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(
                "ttygif needs a POSIX host with /bin/sh (Linux or OHOS)")

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler path from Conan conf, never a bare ${CC}.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or "cc"
        # `CC = gcc` is a plain assignment => only a command-line override wins.
        # R9: -j1.  CFLAGS stays untouched so -DVERSION survives.
        self.run('make -j1 CC="%s"' % cc)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        licdir = os.path.join(self.package_folder, "licenses")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(licdir, exist_ok=True)
        copy(self, "ttygif", src=self.source_folder, dst=bindir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=licdir, keep_path=False)
        exe = os.path.join(bindir, "ttygif")
        if not os.path.isfile(exe):
            raise ConanException("package(): missing build artifact %s" % exe)
        os.chmod(exe, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Application package: hand its own CLI to consumers' run environment
        # (same shape as archives/v/vamps/0.99.2).
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))
