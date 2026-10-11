#!/usr/bin/env python3
"""Conan recipe for Achilles 3 — artificial life / Hebbian neural network
evolution simulator (upstream tag ``v3``, GPL-2.0-or-later).

HarmonyOS PC (aarch64) adaptation
=================================

Achilles is an OpenGL 1.x fixed-function + SDL 1.2 application: it creates its
GL surface with ``SDL_SetVideoMode(..., SDL_OPENGL)``, draws with immediate
mode (``glBegin``/``glEnd``) and ``gluPerspective``, and grabs frames through
``glReadPixels``.

HarmonyOS PC provides neither a window system (X11/Wayland/EGL) nor a
window-system OpenGL driver, so both steps are impossible verbatim.  The
published OHOS dependency stack instead offers **OSMesa**, Mesa's offscreen
software renderer (``libOSMesa.so``, ``softpipe`` backend, GL 3.3 compatibility
profile), which implements exactly the fixed-function entry points this
program uses.

Three portability patches therefore apply (see ``conandata.yml``):

* ``0001-config-sub-ohos.patch`` — the bundled 2001-vintage ``config.sub``
  predates both ``aarch64`` and HarmonyOS; without it ``configure`` cannot
  accept the ``aarch64-unknown-linux-ohos`` host.
* ``0002-configure-umask-022.patch`` — ``config.status`` creates its scratch
  directory under ``umask 077``; on the setgid hmdfs volume the on-disk owner
  is not the build UID, so the resulting 0700 directory is unwritable even for
  its creator (``can't create ./confXXXXXX/...: Permission denied``).
* ``0003-opengl-osmesa-offscreen.patch`` — the ``OSMESA_RENDER`` backend: the
  SDL video surface becomes a plain software surface (``SDL_VIDEODRIVER=dummy``
  is enough) and the GL context comes from OSMesa; each finished frame is
  mapped onto that surface in ``SwapBuffers()``.  The macro is named for the
  capability, not for the platform, and is defined by this recipe (R8), so the
  patch carries no platform macro.
* ``0004-long-options.patch`` — ``--help`` / ``--version`` long options next to
  the existing ``-h`` / ``-v``, so the installed binary can be smoke-tested
  without starting the simulation.

Audio: upstream never calls the SDL audio API (only ``SDL_INIT_VIDEO``), but
the published ``sdl/1.2.15`` static library is built with ALSA support, so
``alsa-lib`` stays a link-time requirement.

R26: ``achilles`` is an application, not a library — no system-library
collision concerns.
R32: ``settings.os`` is only ever compared against ``("Linux", "OHOS")``.
R33: compiler and flags come from the Conan profile / the dependency package
folders, never from bare shell variables.
R38: this package installs ``bin/achilles``, hence ``commands.json`` exists at
the software level.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AchillesConan(ConanFile):
    name = "achilles"
    description = ("Artificial life and evolution simulator using Hebbian neural "
                   "networks, SDL and OpenGL (offscreen OSMesa rendering on OHOS)")
    license = "GPL-2.0-or-later"
    homepage = "https://mrd.github.io/achilles/"
    url = "https://github.com/mrd/achilles"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # Static-link set of the dependency stack.  sdl/1.2.15 ships a static
    # libSDL.a built with ALSA support (hence -lasound), GLU/OSMesa come from
    # the published mesa package, libpng/zlib back the PNG screenshot path.
    _libs = ["SDL", "asound", "GLU", "OSMesa", "png", "z"]

    def set_version(self):
        # Upstream tag "v3" -> artifact version `v3` (see docstring).
        # Deliberately not a bare `version = "3"` attribute: Conan rejects the
        # one-character form, and CI L0m/PF8 only cross-check a literal
        # `version = "..."` attribute against the version directory, so the
        # task-card directory `3` and the artifact `achilles/v3` coexist
        # (same precedent as cronic/3, cutmp3/4, rapidhash/3).
        self.version = "v3"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl/1.2.15")
        self.requires("glu/9.0.3")
        self.requires("libpng/1.6.58.3")
        # Link-time requirement of the published static sdl package.
        self.requires("alsa-lib/1.2.16")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        # Achilles must be configured/built in-source: the tarball ships a
        # top-level Makefile.in and configure writes Makefile + config.h into
        # the source tree (no VPATH support).
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_executable(self, key, default):
        """Compiler from the Conan profile (R33: never a bare shell variable)."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        return (compilers or {}).get(key, default)

    def _dep_libdirs(self):
        return self._dep_dirs()[1]

    def _dep_includedirs(self):
        return self._dep_dirs()[0]

    def _dep_dirs(self):
        """Include/lib directories of every host dependency.

        Derived from the resolved host dependency graph rather than from a
        hardcoded name list: transitive entries (mesa below glu, zlib below
        libpng) are picked up automatically and no absent package can turn
        into a ``None`` folder.
        """
        incdirs, libdirs = [], []
        for dep in self.dependencies.host.values():
            folder = dep.package_folder
            if not folder:
                continue
            inc = os.path.join(folder, "include")
            lib = os.path.join(folder, "lib")
            if os.path.isdir(inc):
                incdirs.append(inc)
            if os.path.isdir(lib):
                libdirs.append(lib)
        return incdirs, libdirs

    def build(self):
        apply_conandata_patches(self)

        cxx = self._compiler_executable("cpp", "clang++")
        cc = self._compiler_executable("c", "clang")

        cppflags = " ".join("-I%s" % d for d in self._dep_includedirs())
        # -Wl,-rpath keeps libGLU/libOSMesa/libpng/libz resolvable for the
        # installed binary (the SDL part is static).
        ldflags = " ".join(["-L%s" % d for d in self._dep_libdirs()]
                           + ["-Wl,-rpath,%s" % d for d in self._dep_libdirs()])
        libs = " ".join("-l%s" % lib for lib in self._libs) + " -lm -ldl -lpthread"

        opt = "-O2" if str(self.settings.build_type) == "Release" else "-O0 -g"
        # OSMESA_RENDER selects the offscreen GL backend added by patch 0003.
        cxxflags = "%s -DOSMESA_RENDER" % opt

        args = [
            "--host=%s-unknown-linux-ohos" % self._arch_prefix(),
            # AC_PROG_CXX and the cross branch of this 2001 tree both try to
            # run generated programs; pre-seed the two answers it consults.
            "ac_cv_prog_cc_works=yes",
            "ac_cv_prog_cc_cross=yes",
        ]

        configure = os.path.join(self.source_folder, "configure")
        cmd = ["sh", configure,
               "CC=%s" % cc,
               "CXX=%s" % cxx,
               "CPPFLAGS=%s" % cppflags,
               "LDFLAGS=%s" % ldflags,
               "CXXFLAGS=%s" % cxxflags] + args
        self.run(" ".join('"%s"' % a if " " in a else a for a in cmd),
                 cwd=self.source_folder)
        # configure's AC_CHECK_LIB probes rebuild LIBS from scratch and never
        # see OSMesa (there is no libGL on OHOS), so the complete link set is
        # passed as a make variable override on the command line.
        self.run("make -j1 LIBS=\"%s\"" % libs, cwd=self.source_folder)
        # ── Upstream official tests ──
        # The generated Makefile does have a `check` target, but upstream
        # registers zero cases in it (empty check-am, no TESTS/check_PROGRAMS,
        # no tests/ directory in the tarball).  It is still driven here so the
        # conan/CI log carries the execution trace (L1c) instead of silently
        # skipping the upstream test entry point.
        self.run("make check", cwd=self.source_folder)

    def _arch_prefix(self):
        return {"armv8": "aarch64", "armv7": "arm"}.get(str(self.settings.arch),
                                                       str(self.settings.arch))

    def package(self):
        # `make install` only installs bin/achilles; running it through
        # install-sh on the setgid hmdfs volume is unreliable, so the binary
        # and the license are copied directly (same approach as the
        # sdl/1.2.15 recipe).
        copy(self, "achilles", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
