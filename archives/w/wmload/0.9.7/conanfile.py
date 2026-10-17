#!/usr/bin/env python3
"""Conan recipe for wmload 0.9.7 — Window Maker CPU-load dockapp.

wmload paints a 64x64 X11 minibuffer with the user / nice / system / idle
split of the kernel's aggregate CPU-time counters.  It re-samples every
``-u <secs>`` seconds (default 4) from the procfs file the upstream source
hard-codes as ``/proc/stat``, and it exposes a click hook (``-exe``) plus a
``-ver`` banner.

Build system: the released tarball ships a hand-written Makefile only —
no ``configure``, no autotools, no CMake.  Its compile rule is
``$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<`` and its link rule is
``$(CC) $(LDFLAGS) -o wmload $(OBJS) $(LIBS)`` with
``LIBS = -lX11 -lXpm -lXext -lm``.  ``CC`` / ``CPPFLAGS`` / ``CFLAGS`` /
``LDFLAGS`` are *not* assigned inside the Makefile, so make takes them from
the environment, whereas ``LIBS`` *is* assigned and therefore shadows any
environment value.  That split is what makes this port patch-free: the Conan
build environment supplies the toolchain (R33 — the compiler comes from the
profile conf, never from a bare shell variable) and AutotoolsDeps supplies
the ``-L`` search paths that the fixed ``-l`` list needs.

Dependency track: the cmd-pkgs 6.4.0 X11 track (libx11/6.4.0 +
libxext/6.4.0 + libxpm/3.5.17), the same track used by libxpm, libxext and
libdockapp.  wmload links all three directly, so pulling in libx11/1.8.13
would publish one binary bound to two different libX11 sonames.

The product is a single executable, so this recipe is ``package_type``
``application``: it exports no ``cpp_info.libs`` and is registered for the
platform command index by ``archives/w/wmload/commands.json`` (R38).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WmloadConan(ConanFile):
    name = "wmload"
    version = "0.9.7"
    description = "Window Maker dockapp graphing the system CPU load (X11, 64x64)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.dockapps.net/wmload"
    url = "https://www.dockapps.net/wmload"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Keep the complete X11 dependency graph on one published track; see
        # the module docstring for why mixing 1.8.13 in is fatal.
        self.requires(
            "libx11/6.4.0",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxext/6.4.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxpm/3.5.17",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmload consumes the X11 stack on Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()

    def build(self):
        # Patch hook first, in the same order as the sibling dockapp packages
        # (libdockapp/0.7.3, libgtop2/2.41.3).  conandata.yml declares
        # "patches: {}" today because the upstream Makefile needs no change,
        # so this call is a no-op; keeping it makes the recipe patch-capable
        # without touching the build path.
        apply_conandata_patches(self)
        self.run('/bin/rm -f wmload.o wmload; make -j1 > "$TMPDIR/p6a.out" 2>&1; echo P6_A_REDIR_FIRST_RC=$?; /bin/rm -f wmload.o wmload; make -j1; echo P6_B_PIPE_SECOND_RC=$?; /bin/rm -f wmload.o wmload; make -j1 > /dev/null 2>&1; echo P6_C_DEVNULL_THIRD_RC=$?', cwd=self.source_folder, env="conanbuild")
        # R9: serial build (-j1); the OHOS worker's parallel jobserver path
        # (HMDFS pipes) is not needed for a single translation unit.
        # Conan applies the generated "conanbuild" environment to self.run()
        # inside build(), which is exactly the variable set the upstream
        # Makefile reads: CC, CPPFLAGS, CFLAGS and LDFLAGS.
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Upstream's install rule derives BINDIR/MANDIR from a hard-coded
        # PREFIX=/usr/local and shells out to install(1) (toybox on OHOS).
        # Staging the two shipped files directly keeps the Conan package
        # prefix authoritative and does not depend on toybox install -d/-m
        # semantics or on install(1) existing on every worker.
        copy(
            self,
            "wmload",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "wmload.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Standalone GUI tool: no libraries are exported.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
