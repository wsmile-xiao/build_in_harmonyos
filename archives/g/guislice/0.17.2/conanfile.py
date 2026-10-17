#!/usr/bin/env python3
"""Conan recipe — GUIslice 0.17.2 (C embedded touchscreen GUI library).

Build system: GUIslice ships no top-level configure/CMake; the Linux build
entry is `examples/linux/Makefile` which compiles the library core directly
from `src/` (GUIslice.c + elem/*.c) together with the SDL2 display driver
(GUIslice_drv_sdl.c). This recipe reproduces that direct-compile layout and
packages a static library + headers for HarmonyOS PC (OHOS) consumers.

HarmonyOS (OHOS) adaptations:
- The published ohpcd sdl2 build has no OpenGL/OpenGLES backend (see
  archives/s/SDL2 recipe, E092), so GUIslice must run in software-renderer
  mode. A new config header `configs/ohos-sdl2-default.h` selects
  DRV_DISP_SDL2 + DRV_TOUCH_SDL with DRV_SDL_RENDER_ACCEL=0, and
  GUIslice_drv_sdl.c is patched to skip SDL_WINDOW_OPENGL when the software
  renderer is in use (patch 0001).
- `GSLC_DEBUG_PRINT("DBG: - OK\n","")` fix in GUIslice_drv_sdl.c: the
  variadic macro expands to `gslc_DebugPrintf(sFmt, __VA_ARGS__)`, which is a
  compile error when the call site passes no vararg (upstream bug under
  clang 15 -Werror environments) (patch 0001).
- Config selection is done via USER_CONFIG_LOADED / USER_CONFIG_INC_FILE /
  USER_CONFIG_INC_FNAME compile definitions pointing at the new OHOS config
  header (same mechanism the upstream examples use).
- test_sdl2.c is patched (patch 0002) to drop the OpenGL window flag and use
  the software renderer so the upstream SDL smoke test runs headless on
  OHOS (SDL_VIDEODRIVER=dummy/offscreen).

R38: GUIslice is a library (produces libguislice.a + headers), not a CLI
tool, so no commands.json is declared.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os

# OHOS SDL2 config header (software renderer) — generated at build time.
# DRV_DISP_SDL2 + DRV_TOUCH_SDL with DRV_SDL_RENDER_ACCEL=0: the ohpcd sdl2
# build has no OpenGL/OpenGLES backend (E092), so the accelerated renderer is
# unavailable and SDL_WINDOW_OPENGL must not be requested (see patch 0002).
_OHOS_CONFIG_HEADER = """\
#ifndef _GUISLICE_CONFIG_OHOS_H_
#define _GUISLICE_CONFIG_OHOS_H_

#ifdef __cplusplus
extern "C" {
#endif

  #define DRV_DISP_SDL2             // LINUX SDL 2.0
  #define DRV_TOUCH_SDL           // LINUX: Use SDL touch driver
  #define GSLC_ROTATE     1
  #define DEBUG_ERR               1
  #define GSLC_FEATURE_COMPOUND       1
  #define GSLC_FEATURE_XTEXTBOX_EMBED 0
  #define GSLC_FEATURE_INPUT          1
  #define GSLC_SD_EN    0
  #define DRV_TOUCH_IN_DISP
  #define GSLC_TOUCH_MAX_EVT    1
  #define GSLC_BMP_TRANS_EN     1
  #define GSLC_BMP_TRANS_RGB    0xFF,0x00,0xFF
  #define GSLC_USE_FLOAT        1
  #define GSLC_DEV_FB       "/dev/fb0"
  #define GSLC_DEV_TOUCH    ""
  #define GSLC_DEV_VID_DRV  "x11"
  #define DRV_SDL_FIX_START     0
  #define DRV_SDL_MOUSE_SHOW    0
  #define DRV_SDL_RENDER_ACCEL 0
  #define GSLC_USE_PROGMEM      0
  #define GSLC_LOCAL_STR        1
  #define GSLC_LOCAL_STR_LEN    30

#ifdef __cplusplus
}
#endif
#endif
"""


class GuisliceConan(ConanFile):
    name = "guislice"
    version = "0.17.2"
    description = "GUIslice embedded touchscreen GUI library in C (SDL2 driver)"
    license = "MIT"
    homepage = "https://github.com/ImpulseAdventure/GUIslice"
    url = ""  # CI fills this
    topics = ("gui", "touchscreen", "sdl2", "embedded", "tft")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # SDL2 + SDL2_ttf are the display/font backends used by the Linux
        # (and thus OHOS) driver; both are published on ohpcd.
        self.requires("sdl2/2.30.10")
        self.requires("sdl2_ttf/2.24.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from the Conan profile conf, not shell env vars
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"

        src = self.source_folder

        # Generate the OHOS SDL2 config header (software renderer). It is a
        # build-time artifact (not a source patch) so it survives refresh-patch
        # regeneration and is selected via USER_CONFIG_INC_FNAME below.
        config_dir = os.path.join(src, "configs")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "ohos-sdl2-default.h")
        if not os.path.exists(config_path):
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(_OHOS_CONFIG_HEADER)

        obj = os.path.join(self.build_folder, "obj")
        os.makedirs(obj, exist_ok=True)

        # Gather include dirs from dependencies (sdl2, sdl2_ttf, freetype...)
        includes = [os.path.join(src, "src")]
        for dep in self.dependencies.values():
            for inc in dep.cpp_info.includedirs:
                includes.append(inc)

        inc_flags = " ".join(f"-I{inc}" for inc in includes)
        pic = "-fPIC" if (self.options.get_safe("fPIC") and not self.options.shared) else ""

        cflags = f"-O2 -Wall {pic} {inc_flags} -DUSER_CONFIG_LOADED -DUSER_CONFIG_INC_FILE"
        # Keep the inner quotes so the preprocessor sees a quoted filename:
        #   #define USER_CONFIG_INC_FNAME "../configs/ohos-sdl2-default.h"
        cflags += r""" -DUSER_CONFIG_INC_FNAME=\"../configs/ohos-sdl2-default.h\""""

        # Compile library core + extended elements + SDL2 display driver
        # Note: use absolute paths — conan's build() cwd is the build folder,
        # not the source folder (basic_layout).
        sources = [os.path.join(src, "src", "GUIslice.c"),
                   os.path.join(src, "src", "GUIslice_drv_sdl.c")]
        import glob as _glob
        sources += sorted(_glob.glob(os.path.join(src, "src", "elem", "*.c")))

        objs = []
        for s in sources:
            o = os.path.join(obj, os.path.basename(s).replace(".c", ".o"))
            self.run(f"{cc} {cflags} -c {s} -o {o}", env="conanbuild")
            objs.append(o)

        # Archive the static library (R26: system-name libs static; here the
        # package is a plain static library)
        ar = comp.get("ar", "llvm-ar") if comp else "llvm-ar"
        lib_dir = os.path.join(self.build_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        lib_path = os.path.join(lib_dir, "libguislice.a")
        self.run(f"{ar} rcs {lib_path} {' '.join(objs)}", env="conanbuild")

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include", "guislice"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "src", "elem"),
             dst=os.path.join(self.package_folder, "include", "guislice", "elem"))
        # OHOS config header (added by patch 0003) — shipped so consumers can
        # select the software-renderer SDL2 config via
        # -DUSER_CONFIG_LOADED -DUSER_CONFIG_INC_FILE
        # -DUSER_CONFIG_INC_FNAME="ohos-sdl2-default.h"
        copy(self, "ohos-sdl2-default.h",
             src=os.path.join(self.source_folder, "configs"),
             dst=os.path.join(self.package_folder, "include", "guislice"),
             keep_path=False)
        copy(self, "libguislice.a", src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["guislice"]
        self.cpp_info.includedirs = ["include/guislice"]
        self.cpp_info.set_property("cmake_file_name", "guislice")
        self.cpp_info.set_property("cmake_target_name", "guislice::guislice")
