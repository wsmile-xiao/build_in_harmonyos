#!/usr/bin/env python3
"""Conan recipe - mupen64plus 2.6.0 (N64 emulator core: r4300 interpreter +
Ari64 new-dynarec with ARM64 backend, SDL2 video/audio frontend API).

Upstream build system: hand-written GNU Makefile (projects/unix/Makefile),
no configure script. Dependency discovery is pkg-config driven but every
probe can be bypassed by pre-defining <DEP>_CFLAGS / <DEP>_LDLIBS make
variables (Makefile uses `ifeq ($(origin ...), undefined)` guards) — that
is the injection seam used here, zero source patch needed.

OHOS / cross-compile adaptation (all through make variables / env):
  - UNAME=Linux: Makefile keys OS detection off `uname -s`; OHOS devices
    report "HarmonyOS" which the Makefile rejects. UNAME is `?=` so it is
    injected from outside.
  - CC/CXX passed on the make command line (Makefile hardcodes
    `CC = $(CROSS_COMPILE)gcc`; command-line vars override file assigns).
  - aarch64 auto-selects DYNAREC=arm64 + NEW_DYNAREC=1 (-DNEW_DYNAREC=4):
    linkage_arm64.S is compiled with $(COMPILE.c) i.e. the C compiler
    driving the integrated assembler; asm_defines_gas.h is generated from
    the compiled asm_defines.o (grep '@ASM_DEFINE' strings) — both work
    unmodified with the OHOS clang 15 toolchain.
  - OSD=0: the on-screen-display needs desktop OpenGL + GLU + freetype2;
    OHOS PC has no desktop GL. OSD is optional (M64P_OSD compile-time
    macro); disabling it keeps the core API fully intact.
  - VULKAN=0: VIDEXT_VULKAN path needs the Vulkan loader; disabled, the
    SDL2/OpenGL video extension remains.
  - OPTFLAGS: upstream default -O3 -flto; -flto yields LLVM bitcode
    objects — fine with the OHOS clang/lld pair, kept as-is.
  - SDL2 (static libSDL2.a from the conan package) is linked into
    libmupen64plus.so; the api_export.ver version script limits exported
    symbols to the m64p_* API so SDL stays an internal implementation
    detail. Final NEEDED: libpng16 / libc++_shared / libc only.
  - Upstream has NO automated test target (Makefile: all/install/uninstall/
    clean; tools/regtests needs a full frontend + ROMs). Test inventory =
    0/0; consumer validation in test_package (8 assertions).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.env import VirtualBuildEnv


class Mupen64plusConan(ConanFile):
    name = "mupen64plus"
    version = "2.6.0"
    description = "Mupen64Plus core - N64 emulator core library (r4300 cached interpreter + new dynarec ARM64 backend, SDL2 frontend API)"
    license = "GPL-2.0-or-later"
    homepage = "https://mupen64plus.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")
        self.requires("sdl2/2.30.10")

    def export_sources(self):
        # No patches for this package (all adaptation via make variables);
        # export_conandata_patches would be a no-op but is kept for schema
        # compliance with the archive quality gate (G1).
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _dep_vars(self):
        """Make variables that bypass every upstream pkg-config probe.

        Values are shell-quoted so spaces survive the self.run() shell
        line (`make VAR='a b'`).
        """
        import shlex
        zlib = self.dependencies["zlib"]
        libpng = self.dependencies["libpng"]
        sdl2 = self.dependencies["sdl2"]
        # sdl2 conan package exposes headers under include/SDL2 (its
        # package_info declares no includedirs, so the default include/
        # is reported); upstream expects the sdl2-config layout where
        # SDL.h is found directly (CFLAGS += -I<prefix>/include/SDL2).
        sdl2_inc = os.path.join(sdl2.package_folder, "include", "SDL2")
        raw = {
            "ZLIB_CFLAGS": f"-I{zlib.cpp_info.includedirs[0]}",
            "ZLIB_LDLIBS": f"-L{zlib.cpp_info.libdirs[0]} -lz",
            "LIBPNG_CFLAGS": f"-I{libpng.cpp_info.includedirs[0]}",
            "LIBPNG_LDLIBS": f"-L{libpng.cpp_info.libdirs[0]} -lpng16",
            "SDL_CFLAGS": f"-I{sdl2_inc} -D_REENTRANT",
            "SDL_LDLIBS": f"-L{sdl2.cpp_info.libdirs[0]} -lSDL2",
        }
        return {k: shlex.quote(v) for k, v in raw.items()}

    def build(self):
        # apply_conandata_patches is a no-op for this package (patches: {}
        # in conandata.yml — adaptation is fully make-variable driven);
        # kept for schema compliance with the archive quality gate (G1).
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        dep_vars = self._dep_vars()
        args = [f"{k}={v}" for k, v in dep_vars.items()]
        args += [
            "OSD=0",      # no desktop OpenGL/GLU/freetype on OHOS PC
            "VULKAN=0",   # no Vulkan loader needed
            f"PREFIX={self.package_folder}",
        ]
        # command-line vars override the Makefile's hardcoded `CC = ...gcc`
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        args += [f"CC={cc}", f"CXX={cxx}"]
        unix_dir = os.path.join(self.source_folder, "projects", "unix")
        os.environ["UNAME"] = "Linux"  # Makefile OS detection (HarmonyOS unsupported upstream)
        self.run(f'make -C "{unix_dir}" -j{os.cpu_count() or 2} all ' + " ".join(args))

    def package(self):
        dep_vars = self._dep_vars()
        args = [f"{k}={v}" for k, v in dep_vars.items()]
        args += [
            "OSD=0", "VULKAN=0",
            f"PREFIX={self.package_folder}",
            f"LIBDIR={os.path.join(self.package_folder, "lib")}",
            f"INCDIR={os.path.join(self.package_folder, "include", "mupen64plus")}",
            f"SHAREDIR={os.path.join(self.package_folder, "res", "mupen64plus")}",
        ]
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        args += [f"CC={cc}", f"CXX={cxx}"]
        unix_dir = os.path.join(self.source_folder, "projects", "unix")
        os.environ["UNAME"] = "Linux"
        # upstream install also creates the SONAME symlink
        self.run(f'make -C "{unix_dir}" install ' + " ".join(args))
        # headers (upstream install already covers m64p_*.h via INCDIR; keep
        # an explicit copy as belt-and-suspenders for include layout)
        copy(self, "m64p_*.h",
             src=os.path.join(self.source_folder, "src", "api"),
             dst=os.path.join(self.package_folder, "include", "mupen64plus"))
        # data files (mupen64plus.ini ROM database + font) under res/
        copy(self, "*", src=os.path.join(self.source_folder, "data"),
             dst=os.path.join(self.package_folder, "res", "mupen64plus"))
        # upstream installs libmupen64plus.so.2.0.0 + SONAME symlink
        # (libmupen64plus.so.2) but no dev symlink; create it so that
        # CMakeDeps/pkg-config consumers resolve -lmupen64plus.
        libdir = os.path.join(self.package_folder, "lib")
        so_real = os.path.join(libdir, "libmupen64plus.so.2.0.0")
        so_dev = os.path.join(libdir, "libmupen64plus.so")
        if os.path.isfile(so_real) and not os.path.exists(so_dev):
            os.symlink("libmupen64plus.so.2.0.0", so_dev)

    def package_info(self):
        self.cpp_info.libs = ["mupen64plus"]
        self.cpp_info.includedirs = [os.path.join("include", "mupen64plus")]
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.set_property("pkg_config_name", "mupen64plus")
