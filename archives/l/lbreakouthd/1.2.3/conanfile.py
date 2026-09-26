#!/usr/bin/env python3
"""Conan recipe — lbreakouthd 1.2.3 (SDL2 breakout game from LGames).

Build system: Autotools (configure + make). Produces a single executable
`lbreakouthd` (src/Makefile.am bin_PROGRAMS, links static libgame.a) plus
levels/themes data and po/ translations.

OHOS adaptation notes:
  - configure.ac shells out to `sdl2-config` for CXXFLAGS/LIBS. The ohpcd
    sdl2 package ships a self-contained sdl2-config in bin/, so we put that
    dir (and the gettext tools dir, for po/) on PATH during configure.
  - configure does NOT reset the shell `LIBS` variable, so the transitive
    static link libraries computed by AutotoolsDeps (freetype/tiff/webp/
    jpeg/z from the SDL2_* deps) are inherited by the generated Makefiles.
  - Patches: config.guess/sub HarmonyOS triplet (E007), configure umask
    (E046), src/sdl.h include order, src/tools.h sys/types.h (uint),
    src/sdl.cpp software-renderer fallback.
  - Upstream has NO test target (no TESTS / check_PROGRAMS / tests/ dir):
    `make check` only runs automake's empty check-am=all-am.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LbreakouthdConan(ConanFile):
    name = "lbreakouthd"
    version = "1.2.3"
    description = "LBreakoutHD — a timeless breakout game with an HD modern theme"
    license = "GPL-3.0-or-later"
    homepage = "https://lgames.sourceforge.net/LBreakoutHD/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0-verified: all published to ohpcd. gettext provides the libintl.a
        # + po/ build tools; the separate libintl package (shared libintl.so)
        # is not used — its undefined-symbol set breaks conftest under
        # --no-allow-shlib-undefined.
        self.requires("sdl2/2.30.10")
        self.requires("sdl2_image/2.6.0")
        self.requires("sdl2_mixer/2.8.1")
        self.requires("sdl2_ttf/2.24.0")
        self.requires("gettext/0.22.5")

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lbreakouthd is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        # In-source build: upstream install-data-local loops over EXTRA_DIST
        # level/theme files with unquoted relative paths, which only works
        # when the build directory IS the source directory.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        # The SourceForge "/download" URL has no .tar.gz suffix; conan's get()
        # infers compression from the filename, so pass it explicitly.
        sources = dict(self.conan_data["sources"])
        backup_urls = sources.pop("backup_urls", [])
        try:
            get(self, **sources, strip_root=True,
                filename="lbreakouthd-1.2.3.tar.gz")
        except ConanException:
            if not backup_urls:
                raise
            self.output.warning(f"Primary URL failed, trying backup: {backup_urls[0]}")
            get(self, url=backup_urls[0], sha256=sources["sha256"],
                strip_root=True, filename="lbreakouthd-1.2.3.tar.gz")

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # --disable-install sets datdir/hiscoredir/configdir to "." so the
        # game's levels/themes ship at the package root and are found
        # relative to the working directory at runtime (the packaged binary
        # is otherwise compiled with prefix=/ → //share/lbreakouthd, which is
        # not reachable on the read-only root FS for the smoke test).
        tc.configure_args.append("--disable-install")
        tc.generate()
        env = Environment()
        for dep in self.dependencies.values():
            # configure conftest programs link shared deps (libfreetype.so,
            # libtiff.so, libwebp.so): the OHOS loader needs LD_LIBRARY_PATH.
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
            # configure.ac calls `sdl2-config --cflags/--libs` and po/ needs
            # msgfmt/msgmerge/xgettext from the gettext package.
            if dep.ref.name in ("sdl2", "gettext"):
                bin_dir = os.path.join(dep.package_folder, "bin")
                if os.path.isdir(bin_dir):
                    env.append_path("PATH", bin_dir)
        env.vars(self, scope="build").save_script("conanbuild_lbo_deps_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM (E074)
        autotools.make(args=["-j1"])
        # L1c: upstream has no test target; `make check` is automake's
        # empty check-am=all-am (documented in test_package/MANIFEST.yml).
        autotools.make(args=["-j1", "check"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Upstream `$(DESTDIR)$(datdir)` concatenates DESTDIR and datdir
        # without a separator; with --disable-install datdir="." the
        # levels/themes/hscr land in a stray "<package_folder>." directory.
        # Merge it into the package root so the data sits beside bin/.
        stray = self.package_folder + "."
        if os.path.isdir(stray):
            for entry in os.listdir(stray):
                shutil.move(os.path.join(stray, entry),
                            os.path.join(self.package_folder, entry))
            os.rmdir(stray)

    def package_info(self):
        # Standalone game executable, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
