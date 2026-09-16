#!/usr/bin/env python3
"""Conan test_package — pdcurses consumer verification (R34).

Compiles and links a curses consumer against the packaged static
libpdcurses + the sdl2 dependency, then executes it headless with the
SDL dummy video driver, asserting real API behaviour (initscr/printw/
refresh/timeout-getch/endwin decide the exit code).

Link order matters for lld: the object file comes first, then libraries.
Only the SDL2 core component is linked (SDL2main/SDL2test are not needed
by curses consumers); its declared OHOS system_libs (ohaudio, EGL, ...)
satisfy libSDL2.a's native dependencies.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


def _abs(base, path):
    return path if os.path.isabs(path) else os.path.join(base, path)


class PdcursesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC", "clang")
        pdc = self.dependencies["pdcurses"]
        sdl2 = self.dependencies["sdl2"]

        pdc_base = getattr(pdc, "package_folder", None) or ""
        incs = [_abs(pdc_base, d) for d in pdc.cpp_info.includedirs]
        pdc_lib = os.path.join(pdc_base, pdc.cpp_info.libdirs[0], "libpdcurses.a")

        # SDL2 core component only (plain cpp_info fallback for non-component recipes)
        infos = (
            [sdl2.cpp_info.components["SDL2"]]
            if "SDL2" in sdl2.cpp_info.components
            else [sdl2.cpp_info]
        )
        sdl2_base = getattr(sdl2, "package_folder", None) or ""
        libdirs, libs = [], []
        for ci in infos:
            incs += [_abs(sdl2_base, d) for d in ci.includedirs]
            libdirs += [_abs(sdl2_base, d) for d in ci.libdirs]
            libs += ["-l" + l for l in ci.libs] + ["-l" + l for l in ci.system_libs]

        flags = " ".join("-I" + i for i in dict.fromkeys(incs))
        ldlibs = " ".join("-L" + d for d in dict.fromkeys(libdirs))
        ldlibs += " " + " ".join(dict.fromkeys(libs))
        # Object first, libraries after (lld is order-sensitive); musl/OHOS
        # libc keeps pthread/dl symbols, the recipe's declared system_libs
        # cover the rest.
        self.run(f"{cc} -O2 {flags} test.c -o test_probe {pdc_lib} {ldlibs}")

    def test(self):
        # Headless SDL: the dummy video driver makes initscr() work without
        # a display. Real execution on device; honest skip on pure cross
        # hosts (compile+link already verified above).
        # LD_LIBRARY_PATH is cleared: the probe is fully static (libpdcurses.a
        # + libSDL2.a + system libs), so a conan/CI-injected library path can
        # only shadow system libs (observed: chipset-pub-sdk relocation noise
        # breaks exec with exit 127 under build_and_test.sh).
        if can_run(self):
            self.run(
                "LD_LIBRARY_PATH= SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy ./test_probe",
                env="conanrun",
            )
        else:
            self.output.warning(
                "cross build: test_probe compiled and linked; execution "
                "skipped on non-runnable host (device run evidence in W3/G2)"
            )
