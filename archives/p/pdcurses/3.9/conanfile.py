#!/usr/bin/env python3
"""Conan recipe — PDCurses 3.9 (SDL2 backend, static library).

PDCurses 3.9 ships no display-less POSIX port: the wmcbrine tree only
provides x11/sdl1/sdl2/wincon/dos/os2 backends. On OHOS the viable
backend is SDL2 (sdl2/2.32.10 published in the ohpcd registry, R35
verified); the X11 and SDL1 flavours have no dependency available. The
SDL2 port compiles the curses core + sdl2 backend into a static
`pdcurses.a` (upstream implements no shared target for this port), so
linking against SDL2 is deferred to consumers.

R51: upstream has no automated test suite — `demos/` are interactive
visual programs (firework/rain/testcurs/...) with no assertions and
there is no `make test`/`check` target; upstream tests = 0, honestly
declared. Real coverage is provided by the consumer test in
test_package/ (R34): headless SDL run via SDL_VIDEODRIVER=dummy with
behavioural assertions (printw/refresh/timeout-getch/endwin).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PdcursesConan(ConanFile):
    name = "pdcurses"
    version = "3.9"
    description = "PDCurses - a curses library for multiple platforms (SDL2 backend)"
    license = "Public Domain"
    homepage = "https://github.com/wmcbrine/PDCurses"
    url = "https://github.com/wmcbrine/PDCurses"
    topics = ("curses", "tui", "sdl2", "terminal", "console")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.32.10")

    def configure(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "PDCurses 3.9 SDL2 port builds a static library only "
                "(upstream does not implement a shared target for this port)"
            )

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pdcurses sdl2 flavour not validated for {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _sdl2_flags(self):
        """Collect include/lib dirs from the sdl2 dependency (component or
        plain cpp_info), absolutized against the dependency package folder."""
        dep = self.dependencies["sdl2"]
        base = getattr(dep, "package_folder", None) or ""
        incs, libdirs, libs = [], [], []
        infos = (
            dep.cpp_info.components.values()
            if dep.cpp_info.components
            else [dep.cpp_info]
        )
        for ci in infos:
            for d in ci.includedirs:
                incs.append(d if os.path.isabs(d) else os.path.join(base, d))
            for d in ci.libdirs:
                libdirs.append(d if os.path.isabs(d) else os.path.join(base, d))
            libs += ["-l" + l for l in ci.libs]
        # dedupe, keep order
        incs = list(dict.fromkeys(incs))
        libdirs = list(dict.fromkeys(libdirs))
        libs = list(dict.fromkeys(libs))
        return incs, libdirs, libs

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder.replace("\\", "/")
        sdl2_dir = src + "/sdl2"
        incs, _libdirs, _libs = self._sdl2_flags()
        sflags = " ".join("-I" + i for i in incs)
        exe = self.conf.get("tools.build:compiler_executables") or {}
        cc = exe.get("c") or os.environ.get("CC", "clang")
        # ohos profile only pins c/cpp; the sysroot ships LLVM binutils.
        ar = exe.get("ar") or os.environ.get("AR", "llvm-ar")
        # Library target only (all -> libs -> pdcurses.a); demos are not built.
        # SDL2 is compile-time-include-only here: the static archive does not
        # link SDL2, consumers link it themselves (see test_package).
        self.run(
            f"make -j1 -C '{sdl2_dir}' PDCURSES_SRCDIR='{src}' "
            f"CC='{cc}' AR='{ar}' SFLAGS='{sflags}'",
            env="conanbuild",
        )

    def package(self):
        src = self.source_folder
        # Upstream builds "pdcurses.a" (no lib prefix); rename on install so
        # consumers can link with the conventional -lpdcurses.
        copy(self, "pdcurses.a", src=os.path.join(src, "sdl2"),
             dst=os.path.join(self.package_folder, "lib"))
        os.rename(
            os.path.join(self.package_folder, "lib", "pdcurses.a"),
            os.path.join(self.package_folder, "lib", "libpdcurses.a"),
        )
        copy(self, "curses.h", src=src,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "panel.h", src=src,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "README.md", src=src,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["pdcurses"]
        self.cpp_info.bindirs = []
