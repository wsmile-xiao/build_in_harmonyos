#!/usr/bin/env python3
"""Conan recipe — kxl 1.2.4 (Kacchan X Windows System Library).

Adapted for HarmonyOS / OpenHarmony PC.  The library now links only
against the X.Org X11 transport stack; audio is left to the OHOS native
audio framework (OHAudio) and is no longer wired into the library at
build time.

Why CMake (instead of upstream autotools):
  Upstream KXL's tarball ships only configure.ac + Makefile.am.  Building
  those via autoreconf requires `aclocal`/`automake`/`libtoolize`,
  none of which are installed on the OHOS conan worker image.  Using
  conan's CMakeDeps gives us direct access to the libx11 CMake config
  (libx11Config.cmake / libx11Targets.cmake) the same way the harfbuzz
  and pango recipes do, without the autotools bootstrap.

Dependency chain (conan CMakeDeps / PkgConfigDeps):

    kxl/1.2.4 (libKXL.so, this recipe, CMake build)
        └─ libx11/6.4.0  (Conan version = cmd-pkgs/SONAME id; upstream is libX11 1.8.10)
               ├─ xorgproto/2025.1
               ├─ xtrans/1.6.0
               └─ libxcb/1.16 → libxau / libxdmcp / xcb-proto

CI remotes use plain name/version refs (no @user/channel). Prefer the
in-tree libx11/6.4.0 recipe so L0i-1 can export + --build=missing when
the package is not yet published.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class KxlConan(ConanFile):
    name = "kxl"
    version = "1.2.4"
    description = "KXL X11 graphics helpers (Xlib-based, audio stripped)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Quipyowert2/libKXL"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Do NOT force libx11:shared=False — the published ohpcd binary is
        # the default shared=True package ID. Forcing static creates a
        # different package_id that is missing from the remote and triggers
        # a from-source rebuild of libx11 (which is flaky / out of scope
        # for this recipe).

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kxl supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # Upstream KXL only consumes Xlib.  libx11/6.4.0 is the published
        # Conan id for upstream libX11 1.8.10 (SONAME 6.4.0); it already
        # pulls xorgproto / xtrans / libxcb transitively.
        #
        # Use bare refs (no @ohpcd/stable) — CI remotes store plain
        # name/version.  `headers=True` keeps KXL.h → <X11/Xlib.h> include
        # dirs visible to consumers under Conan 2.x CMakeDeps.
        self.requires("libx11/6.4.0", headers=True, libs=True)

    def layout(self):
        # cmake_layout puts artefacts in
        # build/<Release|Debug>/...  which makes it trivial to spot the
        # *.so + headers without writing extra install() glob logic.
        cmake_layout(self, src_folder="src_root")

    def source(self):
        # Use strip_root=True so the upstream tarball's top-level
        # "libKXL-1.2.4/" directory is unwrapped to "src_root/".
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # Always build both shared AND static.  Shared is the canonical
        # `kxl::kxl` target; static `libKXL.a` lets the test_package
        # consumer statically link the test binary, which is the only way
        # to skip OHOS's loader namespace ACL (the loader refuses to
        # dlopen() shared libraries from /storage/... paths).
        if self.options.shared:
            tc.variables["KXL_BUILD_SHARED"] = "ON"
            tc.variables["KXL_BUILD_STATIC"] = "ON"
        else:
            tc.variables["KXL_BUILD_SHARED"] = "OFF"
            tc.variables["KXL_BUILD_STATIC"] = "ON"
        if self.settings.os == "OHOS":
            tc.variables["KXL_ENABLE_AUDIO"] = "OFF"
            # OHOS SDK toolchain sets CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY,
            # which masks the CMAKE_PREFIX_PATH entry that conan's CMakeDeps
            # generator puts the libx11/libxcb/.../xtrans config files into.
            # Flip every *_MODE_* to BOTH so find_package(<dep>) can locate the
            # <dep>-config.cmake files emitted under <build>/generators/.
            tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
            tc.variables["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] = "BOTH"
            tc.variables["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] = "BOTH"
        else:
            tc.variables["KXL_ENABLE_AUDIO"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Patches 0003 (stdint) and 0004 (snprintf) live within the
        # upstream src/KXL.{h,c} files; the CMake patch (0006) lays
        # down a CMakeLists.txt that consumes them.

        # On OHOS (or whenever the consumer opts out of audio) we replace
        # KXLsound.c with a no-op stub so we don't pull linux/soundcard.h
        # or libpulse-simple into the build.
        if self.settings.os == "OHOS":
            sound_c = os.path.join(self.source_folder, "src", "KXLsound.c")
            os.makedirs(os.path.dirname(sound_c), exist_ok=True)
            with open(sound_c, "w", encoding="utf-8") as f:
                f.write(_kxl_audio_stub())

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # kxl's exported CMake target must transitively carry the X.Org
        # transport chain's include dirs / link flags / system libs to
        # downstream consumers.  Conan 2.x propagates those via the
        # `cpp_info.components[<name>]` mechanism — top-level
        # `cpp_info.requires` only mirrors link flags, not include paths.
        #
        # We expose TWO components: `libkxl` (the canonical SHARED
        # `kxl::kxl` target, .so) and `libkxl_static` (the STATIC
        # `kxl::kxl_static` target, .a).  Both ship in the package's
        # lib/ directory; the OHOS loader refuses to dlopen() the .so
        # from /storage/ paths, so consumers on OHOS link statically
        # via `kxl::kxl_static`.  Linux/desktop consumers can pick
        # either via the `shared` option.
        self.cpp_info.components["libkxl"].set_property(
            "cmake_target_name", "kxl::kxl"
        )
        self.cpp_info.components["libkxl"].set_property(
            "cmake_file_name", "kxl"
        )
        self.cpp_info.components["libkxl"].set_property(
            "pkg_config_name", "kxl"
        )
        self.cpp_info.components["libkxl"].libs = ["KXL"]
        self.cpp_info.components["libkxl"].includedirs = ["include"]
        self.cpp_info.components["libkxl"].system_libs = ["dl", "pthread"]
        self.cpp_info.components["libkxl"].requires = [
            "libx11::libx11",
        ]

        # Static variant — separate component so consumers can link
        # against libKXL_static.a without dragging in dlopen() of the .so.
        self.cpp_info.components["libkxl_static"].set_property(
            "cmake_target_name", "kxl::kxl_static"
        )
        self.cpp_info.components["libkxl_static"].set_property(
            "cmake_file_name", "kxl"  # same file_name; the two are
                                       # aliased inside kxlConfig.cmake
        )
        self.cpp_info.components["libkxl_static"].libs = ["KXL_static"]
        self.cpp_info.components["libkxl_static"].includedirs = ["include"]
        self.cpp_info.components["libkxl_static"].system_libs = ["dl", "pthread"]
        self.cpp_info.components["libkxl_static"].requires = [
            "libx11::libx11",
        ]


# Module-level helper so build() can call `KxlConan._kxl_audio_stub()`.
def _kxl_audio_stub():
    """Minimal OHOS stub for KXLsound.c — satisfies linker, no-op at runtime."""
    return (
        "/* KXLsound.c - OHOS audio stub (auto-generated by conanfile).\n"
        " *\n"
        " * Upstream KXLsound.c drives either OSS (/dev/dsp + ioctl) or\n"
        " * PulseAudio (libpulse-simple).  Neither is available on\n"
        " * HarmonyOS, so this re-adaptation links an audio-no-op library\n"
        " * against the X.Org transport chain (libx11/libxcb/libxau/\n"
        " * libxdmcp/xtrans).  Apps that need audio should integrate\n"
        " * OHAudio directly; KXL's audio API surface remains declared in\n"
        " * KXL.h for ABI compat.\n"
        " */\n"
        "#include <stdio.h>\n"
        '#include "KXL.h"\n'
        "\n"
        "Bool KXL_SoundOk = False;\n"
        "\n"
        "void KXL_InitSound(const char *path, char **fname) {\n"
        "    (void)path; (void)fname;\n"
        "    KXL_SoundOk = False;\n"
        "}\n"
        "void KXL_EndSound(void) { KXL_SoundOk = False; }\n"
        "void KXL_PlaySound(Uint16 no, KXL_Command action) {\n"
        "    (void)no; (void)action;\n"
        "}\n"
        "void KXL_LoadSoundData(const char *path, char **fname) {\n"
        "    (void)path; (void)fname;\n"
        "}\n"
        "void KXL_SoundServer(void) {}\n"
    )
