#!/usr/bin/env python3
"""Conan test_package — guislice 0.17.2 (L1 consumer test for OHOS).

Builds and runs a real consumer program that uses the GUIslice public API
(gslc_Init with the SDL2 display driver, page/element creation, page switch,
draw + update cycles) against the installed package, exactly as a
business-layer component would. Runs headless with SDL_VIDEODRIVER=dummy
(software renderer) — this is the documented consumer-verification test and
also serves as the HarmonyOS-specific runtime test (R34: no print-only
stubs; observable assertions on init/element/page/draw results).
"""
import os

from conan import ConanFile


class GuisliceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"

        # Include dirs: guislice package + all transitive deps (sdl2, sdl2_ttf, freetype)
        includes = []
        libs = []
        libdirs = []
        for dep in self.dependencies.values():
            includes.extend(dep.cpp_info.includedirs)
            libdirs.extend(dep.cpp_info.libdirs)
            libs.extend(dep.cpp_info.libs)

        inc_flags = " ".join(f"-I{inc}" for inc in includes)
        lib_flags = " ".join(f"-L{d}" for d in libdirs)
        link_libs = " ".join(f"-l{l}" for l in libs)

        # Config selection + OHOS SDL2 software-renderer config (shipped in package).
        # Escape the inner quotes so the preprocessor sees a quoted filename.
        defines = ("-DUSER_CONFIG_LOADED -DUSER_CONFIG_INC_FILE "
                   r''' -DUSER_CONFIG_INC_FNAME=\"ohos-sdl2-default.h\"''')

        self.run(
            f"{cc} -O2 {inc_flags} {defines} -o test_guislice test.c "
            f"{link_libs} {lib_flags} -lm",
            env="conanbuild",
        )

    def test(self):
        # Headless: dummy video driver, software renderer (OHOS SDL2 has no
        # OpenGL backend, see recipe notes / patch 0001)
        self.run("SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy ./test_guislice",
                 env="conanrun")