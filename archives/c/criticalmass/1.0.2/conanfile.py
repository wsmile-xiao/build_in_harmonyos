#!/usr/bin/env python3
"""Critical Mass 1.0.2 - HarmonyOS PC (aarch64) Conan recipe.

Adaptation notes
================
* SDL 1.2 stack: the SDL 1.2 API is supplied by sdl12-compat/1.2.68, with
  SDL_image and SDL_mixer coming from the sibling recipes in this repo.
  SDL discovery: this old Autotools stack (automake 1.4 era) relies on a
  `sdl-config` script and on AC_CHECK_LIB(SDL-1.2), never on pkg-config.
  patches/0003 adds AC_ARG_VAR(SDL_CFLAGS, SDL_LIBS) so both are handed to
  configure explicitly (same technique as the sdl-image recipe), which also
  keeps the sdl12-compat headers (include/SDL) on the compile path for the
  `#include <SDL_image.h>` / `#include <SDL_mixer.h>` / "SDL.h" sites.
* GL: HarmonyOS has no libGL.so, so configure.in:109-110's AC_CHECK_LIB(GL)
  would fail.  `--enable-dyngl` makes the game resolve GL at runtime through
  SDL_GL_GetProcAddress (DYNAMIC_GL), which is the upstream-supported path.
* Cross mode: the OHOS SDK is clang/libc++/musl based; the dual triplet
  --build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos pins
  autoconf into cross-compiling mode, so the "can we run conftest" probes
  (unsigned ELF cannot run in the worker sandbox) are skipped entirely.
  The bundled 2012 config.guess/config.sub cannot identify -ohos, so modern
  FSF 2024 config.guess/config.sub from files/ are copied into the source
  root first (same technique as the cheops recipe).
* Data: upstream builds resource.dat with tools/Packer; patches/0006 drops
  that generation step and makes the game read the data/ directory directly
  from $(pkgdatadir)/data.  data/ is not an automake install target, so the
  six data subdirs (bitmaps/models/sounds/levelpacks/paths/system) are copied
  into share/Critical_Mass/data in package() (only music/lg-criti.xm is a
  pkgdata_DATA install target upstream).
* Tests: upstream ships no test suite at all (no test/ dir, no AC_CONFIG_
  TESTDIR/TESTS).  test_package/ runs the freshly built binary with
  `critter --version` (patches/0004 makes it exit before SDL/GL init) and
  asserts the "Critical_Mass 1.0.2" banner.
* OHOS ELF binaries must be self-signed in package() (llvm-objcopy
  --remove-section .codesign + binary-sign-tool sign -selfSign 1, julius
  recipe precedent), otherwise test_package fails with Operation not
  permitted.
"""
import glob
import os
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class CriticalMassConan(ConanFile):
    name = "criticalmass"
    version = "1.0.2"
    description = (
        "Critical Mass (Critter) - SDL 1.2/OpenGL space shooting game "
        "by Frank Becker (GPL-2+)"
    )
    license = "GPL-2.0-or-later"
    homepage = "http://criticalmass.sourceforge.net/"
    topics = ("game", "sdl", "sdl1.2", "opengl", "shooter", "ohos")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        # Bundle modern FSF config.guess/config.sub (aarch64-ohos aware) so
        # configure can run in cross mode (cheops recipe precedent).
        copy(self, "*",
             os.path.join(self.recipe_folder, "files"),
             os.path.join(self.export_sources_folder, "files"),
             keep_path=True)

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"criticalmass supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # SDL 1.2 API (SDL.h / libSDL-1.2) + image/mixer add-ons; all real
        # build-time dependencies declared explicitly (no host-machine luck).
        self.requires("sdl12-compat/1.2.68")
        self.requires("sdl-image/1.2.12")
        self.requires("sdl-mixer/1.2.12")
        self.requires("libpng/1.6.58")  # configure.in checks png16
        self.requires("curl/8.15.0.1")  # game/OnlineUpdate.cpp
        # zlib is a direct dependency: game/main.cpp calls zlibVersion() and
        # configure.in checks `z`; declared explicitly (no host-machine luck).
        self.requires("zlib/1.3.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _copy_gnu_config(self):
        """Drop modern config.guess/config.sub into the source root.

        The 2012 tarball copies cannot identify aarch64-unknown-linux-ohos;
        the FSF 2024 copies understand it.  config.guess is kept for
        completeness but is never executed because we always pass --build.
        """
        for name in ("config.guess", "config.sub"):
            src = os.path.join(self.export_sources_folder, "files", name)
            if os.path.isfile(src):
                copy(self, name,
                     os.path.dirname(src),
                     os.path.join(self.source_folder))
            else:
                self.output.warning(f"bundled {name} not found; configure may fail")

    def _fix_umask_077(self):
        # HMDFS: temp dirs that config.status/conftest create with umask 077
        # end up without group-write permission, so writes fail with
        # "Permission denied" (configure:4800/4805). Relax to 022 (same fix
        # as the cheops/pakchois recipes).
        for pattern in ("configure", "config.guess", "config.sub"):
            path = os.path.join(self.source_folder, pattern)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8", errors="ignore") as handle:
                    text = handle.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text.replace("umask 077", "umask 022"))

    def _freeze_autotools(self):
        """Pin timestamps so make never regenerates the autotools files.

        This tarball's configure.in (patched by 0001/0002/0003/0005) is newer
        than the shipped configure, so make would normally re-run autoconf
        (and automake/aclocal) in the build.  The regenerated files come from
        autoconf 2.72 and bring back a 077 umask, which breaks the build with
        "confbCr3zr/subs1.awk: Permission denied".  Touch configure / aclocal.m4 /
        config.guess|sub / Makefile.in (source tree) and config.status /
        Makefile (build tree) into the present so make sees nothing to
        regenerate; the 022 umask fix in configure then survives to make.
        """
        now = time.time()
        src = self.source_folder
        build = self.build_folder
        # source-tree files that make would regenerate from configure.in /
        # Makefile.am (all must be newer than their inputs)
        for root, _dirs, files in os.walk(src):
            for name in files:
                if name in ("configure", "aclocal.m4", "config.guess",
                            "config.sub") or name.endswith(".in"):
                    path = os.path.join(root, name)
                    if os.path.isfile(path):
                        os.utime(path, (now, now))
        # build-tree files regenerated from configure / config.status
        for root, _dirs, files in os.walk(build):
            for name in files:
                if name in ("config.status", "config.log", "Makefile",
                            "config.h") or name.endswith(".h") and name != "config.h":
                    path = os.path.join(root, name)
                    if os.path.isfile(path):
                        os.utime(path, (now, now))

    def generate(self):
        sdl12_prefix = self.dependencies["sdl12-compat"].package_folder
        sdl_libdir = os.path.join(sdl12_prefix, "lib")
        # sdl12-compat publishes the compatibility library under both the
        # drop-in SDL 1.2 name and the plain SDL name; use whichever is
        # actually present in the package that got resolved.
        if any(
            os.path.exists(os.path.join(sdl_libdir, name))
            for name in ("libSDL-1.2.so", "libSDL-1.2.a")
        ):
            sdl_lib = "-lSDL-1.2"
        else:
            sdl_lib = "-lSDL"

        sdl_img = self.dependencies["sdl-image"].package_folder
        sdl_mix = self.dependencies["sdl-mixer"].package_folder
        # SDL.h lives in include/SDL and game sources use both "SDL.h" and
        # <SDL_image.h>/<SDL_mixer.h>, so both include spellings are needed
        # for each of the three SDL packages.
        sdl_cflags = " ".join(
            "-I{} -I{}".format(os.path.join(p, "include", "SDL"),
                               os.path.join(p, "include"))
            for p in (sdl12_prefix, sdl_img, sdl_mix)
        )
        sdl_libs = "-L{} -Wl,-rpath-link,{} {}".format(sdl_libdir, sdl_libdir, sdl_lib)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                # GL resolved at runtime (no libGL.so on OHOS)
                "--enable-dyngl",
                # AC_ARG_VAR overrides from patches/0003; there is no usable
                # sdl-config in the sdl12-compat package
                "SDL_CFLAGS=" + sdl_cflags,
                "SDL_LIBS=" + sdl_libs,
            ]
        )
        if self.settings.os == "OHOS":
            # Pin autoconf into cross mode so its conftest run probes are
            # skipped (unsigned ELF cannot run in the worker sandbox).
            tc.configure_args.extend(
                [
                    "--build=x86_64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self._copy_gnu_config()
        # HMDFS: relax the 077 umask config.status/conftest use for temp dirs
        # (cheops precedent), and point TMPDIR at a writable build-folder dir.
        self._fix_umask_077()
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        # HMDFS quirk: -j1 avoids parallel mkfifo/jobserver issues
        # (julius/cheops precedent).
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS: after configure, pin the autotools timestamps so make cannot
        # regenerate configure/Makefile.in from the patched configure.in
        # (which would bring back autoconf 2.72 output and a 077 umask).
        self._freeze_autotools()
        autotools.make(args=["-j1"])

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

        # data/ is not an automake install target (only music/lg-criti.xm is
        # pkgdata_DATA); the game (patches/0006) reads it from
        # $(pkgdatadir)/data = share/Critical_Mass/data at runtime.
        pkgdatadir = os.path.join(self.package_folder, "share", "Critical_Mass")
        for sub in ("bitmaps", "models", "sounds", "levelpacks", "paths", "system"):
            copy(self, "*",
                 src=os.path.join(self.source_folder, "data", sub),
                 dst=os.path.join(pkgdatadir, "data", sub))

        # OHOS ELF must be self-signed, otherwise test_package runs fail
        # with Operation not permitted (julius precedent).
        self._sign_binaries()

    def _sign_binaries(self):
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in glob.glob(os.path.join(bindir, "*")):
            if not os.path.isfile(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # critter is a CLI application, not a library
        self.cpp_info.bindirs = ["bin"]
