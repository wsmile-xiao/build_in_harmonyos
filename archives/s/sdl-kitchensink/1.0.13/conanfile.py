#!/usr/bin/env python3
"""Conan recipe - sdl-kitchensink 1.0.13 (SDL2/FFmpeg audio/video playback).

CMake build system, C99. Requires sdl2/2.30.10 (mandatory, find_package(SDL2
REQUIRED)), ffmpeg/8.1.2 components avcodec/avformat/avutil/swscale/swresample
(found via upstream cmake/Findffmpeg.cmake) and libass/0.17.5 (found via
upstream cmake/Findass.cmake; USE_DYNAMIC_LIBASS=OFF -> direct link).

OHOS adaptation notes:
  - Upstream finds deps through module-mode find modules (FindSDL2/Findffmpeg/
    Findass.cmake) whose search paths are /usr/local,/usr,/opt only. Inject the
    per-component find_* cache variables so the modules resolve to the Conan
    package folders (same approach as sdl2_image/sdl2_mixer).
  - E092: CMake does not know HarmonyOS; use CMAKE_SYSTEM_NAME=Linux with
    CMAKE_SYSTEM_PROCESSOR=aarch64; CMake 4.x needs CMAKE_POLICY_VERSION_MINIMUM.
  - BUILD_SHARED/BUILD_STATIC follow self.options.shared: static package builds
    the SDL_kitchensink_static target only (shared lib pulls sdldeps at runtime).
  - ffmpeg+libass are shared (their recipes build .so); the static kitchensink
    links them directly - add -L/-rpath-link through the dep libdirs so
    transitive NEEDED resolve at link time (sdl2_image precedent).
  - Upstream has NO test target (CMakeLists.txt has no enable_testing/add_test;
    CI workflow only runs make -j2). Test inventory = 0/0.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

import os


class SdlKitchensinkConan(ConanFile):
    name = "sdl-kitchensink"
    version = "1.0.13"
    description = "SDL_kitchensink - SDL2/FFmpeg based audio and video playback library"
    license = "MIT"
    homepage = "https://github.com/katajakasa/SDL_kitchensink"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("ffmpeg/8.1.2")
        self.requires("libass/0.17.5")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Upstream consumes deps through MODULE-mode finders (FindSDL2/
        # Findffmpeg/Findass.cmake) that populate SDL2_INCLUDE_DIRS /
        # FFMPEG_INCLUDE_DIRS / FFMPEG_LIBRARIES. The Conan toolchain force-sets
        # CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON (line ~137), so find_package(SDL2)
        # and find_package(ffmpeg COMPONENTS ...) resolve through CMakeDeps
        # config files, which only define :: targets and leave those aggregate
        # variables empty. Inject the aggregate variables directly instead.

        # SDL2 (module mode) - upstream FindSDL2.cmake searches /usr... only
        sdl2 = self.dependencies["sdl2"]
        if sdl2.package_folder:
            tc.cache_variables["SDL2_INCLUDE_DIRS"] = os.path.join(sdl2.package_folder, "include/SDL2")
            tc.cache_variables["SDL2_INCLUDE_DIR"] = os.path.join(sdl2.package_folder, "include/SDL2")
            tc.cache_variables["SDL2_LIBRARIES"] = os.path.join(sdl2.package_folder, "lib/libSDL2.a")
            tc.cache_variables["SDL2_LIBRARY"] = os.path.join(sdl2.package_folder, "lib/libSDL2.a")

        # FFmpeg components (module mode) - Findffmpeg.cmake per-component vars
        ffmpeg = self.dependencies["ffmpeg"]
        if ffmpeg.package_folder:
            inc = os.path.join(ffmpeg.package_folder, "include")
            lib = os.path.join(ffmpeg.package_folder, "lib")
            libs = []
            for comp in ("avcodec", "avformat", "avutil", "swscale", "swresample"):
                tc.cache_variables[f"{comp}_INCLUDE_DIR"] = inc
                tc.cache_variables[f"{comp}_LIBRARY"] = os.path.join(lib, f"lib{comp}.so")
                libs.append(os.path.join(lib, f"lib{comp}.so"))
            tc.cache_variables["FFMPEG_INCLUDE_DIRS"] = inc
            tc.cache_variables["FFMPEG_LIBRARIES"] = ";".join(libs)

        # libass (module mode) - upstream Findass.cmake expects ass/ass.h
        libass = self.dependencies["libass"]
        if libass.package_folder:
            tc.cache_variables["ASS_INCLUDE_DIRS"] = os.path.join(libass.package_folder, "include")
            tc.cache_variables["ASS_INCLUDE_DIR"] = os.path.join(libass.package_folder, "include")
            tc.cache_variables["ASS_LIBRARIES"] = os.path.join(libass.package_folder, "lib/libass.so")
            tc.cache_variables["ASS_LIBRARY"] = os.path.join(libass.package_folder, "lib/libass.so")

        tc.variables["BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["USE_DYNAMIC_LIBASS"] = "OFF"

        # Shared transitive deps (.so with NEEDED): -L + -rpath-link resolve at
        # link time for the static kitchensink target
        libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                for ld in dep.cpp_info.libdirs:
                    if ld and os.path.isdir(ld) and ld not in libdirs:
                        libdirs.append(ld)
        if libdirs:
            flags = " ".join("-L{0} -Wl,-rpath-link,{0}".format(d) for d in libdirs)
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = flags
            tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = flags

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])
        # Upstream has no test target; inventory = 0/0 (see module docstring)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        libname = "SDL_kitchensink_static" if not self.options.shared else "SDL_kitchensink"
        self.cpp_info.libs = [libname]
        # Package name has a hyphen, which is invalid in CMake target names.
        # Expose an underscore-clean file/target name for consumers.
        self.cpp_info.set_property("cmake_file_name", "sdl_kitchensink")
        self.cpp_info.set_property("cmake_target_name", "sdl_kitchensink::sdl_kitchensink")
        # Headers install to include/kitchensink/*.h; consumers include
        # <kitchensink/kitchensink.h>, whose headers do #include <SDL_*.h>.
        # sdl2's headers live in its include/SDL2/ dir, so propagate that path
        # to consumers (same approach as sdl2_image).
        self.cpp_info.includedirs = ["include"]
        sdl2 = self.dependencies["sdl2"]
        if sdl2.package_folder:
            self.cpp_info.includedirs.append(os.path.join(sdl2.package_folder, "include/SDL2"))
        self.cpp_info.requires = [
            "sdl2::sdl2",
            "ffmpeg::avcodec",
            "ffmpeg::avformat",
            "ffmpeg::avutil",
            "ffmpeg::swscale",
            "ffmpeg::swresample",
            "libass::ass",
        ]