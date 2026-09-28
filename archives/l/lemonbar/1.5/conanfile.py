#!/usr/bin/env python3
"""Conan recipe for lemonbar 1.5 — a featherweight xcb-based status bar.

lemonbar reads a small markup language from stdin and renders it as an X11
dock/status bar.  The upstream tarball is a plain POSIX Makefile project with
no configure step:

    * make          — builds `lemonbar` from lemonbar.c + utils.c
    * make debug    — same with -g3 -pedantic -Wconversion
    * make doc      — runs pod2man over README.pod to produce lemonbar.1
    * make install  — installs the binary and the man page
    * make clean    — removes objects and the binary

Adaptation notes (HarmonyOS PC, aarch64):
    * Zero upstream patches.  The unmodified Makefile builds with the OHOS SDK
      clang (the compiler path comes from Conan conf, never a shell variable —
      R33).
    * X protocol binding comes from the published Conan package
      libxcb/1.17.0.1 (OHOS armv8 binary).  lemonbar links the core `xcb`
      library plus the `xcb-randr` / `xcb-xinerama` extension libraries, which
      the libxcb recipe declares as separate components.
    * The tag tarball has no `.git`, so the Makefile's
      `GIT_DESC=$(shell test -d .git && git describe --always)` probe yields
      nothing and VERSION silently falls back to the hard-coded 1.4 that
      upstream never bumped.  A command-line assignment overrides every
      Makefile assignment, so build() passes `VERSION=1.5` explicitly and the
      artifact self-describes as 1.5.
    * Dependency include/lib directories are handed to the Makefile through the
      CFLAGS/LDFLAGS *environment* (appended by the Makefile's `+=  ` rules).
      Passing them as make command-line variables would clobber the upstream
      `-Wall -std=c99 -Os -DVERSION -D_GNU_SOURCE` defaults.
    * The binary is linked with an `$ORIGIN` rpath and its runtime shared
      libraries (libxcb + extensions + libXau + libXdmcp) are copied next to it
      in bin/ so the package is self-contained — the OHOS musl loader ignores
      LD_LIBRARY_PATH, and the CI worker has no system libxcb.
    * Upstream ships no test suite (no check/TESTS target, no test/ directory
      and no test sources in the tarball); the audit is recorded in
      test_package/MANIFEST.yml.  test_package really executes the installed
      binary.
Artifacts: bin/lemonbar + bundled runtime .so files (software-level
commands.json declares the CLI, R38).
License: MIT.
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


class LemonbarConan(ConanFile):
    name = "lemonbar"
    version = "1.5"
    description = "A featherweight, lemon-scented, bar based on xcb"
    license = "MIT"
    homepage = "https://github.com/LemonBoy/bar"
    url = "https://github.com/LemonBoy/bar"
    topics = ("xcb", "x11", "statusbar", "bar", "panel", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # Runtime shared objects required by the produced binary, grouped by the
    # Conan package that publishes them.  libXau/libXdmcp are DT_NEEDED of
    # libxcb.so.1 itself; they are declared as run requirements above so their
    # package_folder is resolvable here.
    RUNTIME_LIBS = (
        ("libxcb", "libxcb*.so*"),
        ("libxau", "libXau*.so*"),
        ("libxdmcp", "libXdmcp*.so*"),
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Plain POSIX Makefile project: build in the source folder.
        self.folders.build = "."

    def requirements(self):
        # Header + link surface for <xcb/xcb.h>.  transitive_headers/libs keep
        # the protocol headers and the extension libraries reachable.
        self.requires("libxcb/1.17.0.1", transitive_headers=True, transitive_libs=True)
        # Runtime-only companions of libxcb.so.1 (see RUNTIME_LIBS).
        # libxau must match the version libxcb/1.17.0.1 itself depends on
        # (1.0.12); pinning 1.0.11 here produced a graph version conflict.
        self.requires("libxau/1.0.12", run=True)
        self.requires("libxdmcp/1.1.5", run=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ helpers

    def _dep_dir(self, ref, kind):
        """Return a dependency's package-relative include/ or lib directory."""
        dep = self.dependencies[ref]
        dirs = dep.cpp_info.includedirs if kind == "include" else dep.cpp_info.libdirs
        fallback = "include" if kind == "include" else "lib"
        return os.path.join(dep.package_folder, dirs[0] if dirs else fallback)

    # ---------------------------------------------------------------------- build

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException("lemonbar requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"

        include_dirs = [self._dep_dir("libxcb", "include")]
        lib_dirs = [
            self._dep_dir("libxcb", "lib"),
            self._dep_dir("libxau", "lib"),
            self._dep_dir("libxdmcp", "lib"),
        ]

        # Appended to (never replacing) whatever the profile already exports:
        # the Makefile uses `CFLAGS += ` / `LDFLAGS += `, and for an environment
        # variable those append rules do apply.  `$ORIGIN` is single-quoted so
        # that the shell Make uses to run the link line cannot expand it.
        os.environ["CFLAGS"] = (
            os.environ.get("CFLAGS", "")
            + " "
            + " ".join("-I{0}".format(path) for path in include_dirs)
        ).strip()
        os.environ["LDFLAGS"] = (
            os.environ.get("LDFLAGS", "")
            + " "
            + " ".join("-L{0}".format(path) for path in lib_dirs)
            + " -Wl,--disable-new-dtags -Wl,-rpath,'$ORIGIN'"
        ).strip()

        # R9: -j1.  VERSION on the command line beats every assignment in the
        # Makefile (including the conditional git-describe override that comes
        # back empty for a tag tarball, see the module docstring).
        self.run("make -j1 CC={0} VERSION={1}".format(cc, self.version))

        if not os.path.isfile(os.path.join(self.build_folder, "lemonbar")):
            raise ConanException("lemonbar build produced no `lemonbar` executable")

    # -------------------------------------------------------------------- package

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        # Direct copy: the upstream `install` target needs install(1), which is
        # not guaranteed to be on PATH in the CI build environment.
        copy(self, "lemonbar", src=self.build_folder, dst=bindir, keep_path=False)
        os.chmod(os.path.join(bindir, "lemonbar"), 0o755)
        # Bundle the runtime shared objects next to the binary so that the
        # $ORIGIN rpath resolves them on OHOS (the musl loader ignores
        # LD_LIBRARY_PATH and the worker ships no system libxcb).
        for ref, pattern in self.RUNTIME_LIBS:
            dep = self.dependencies[ref]
            libdirs = dep.cpp_info.libdirs or ["lib"]
            src = os.path.join(dep.package_folder, libdirs[0])
            if os.path.isdir(src):
                copy(self, pattern, src=src, dst=bindir, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
