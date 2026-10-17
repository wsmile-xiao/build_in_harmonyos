#!/usr/bin/env python3
"""Conan recipe - sdl2-image 2.8.12 (SDL_image image loading library).

CMake build system, C. Requires sdl2/2.30.10 (mandatory) plus
libtiff/4.7.2 and libwebp/1.6.0 (optional format support).
OHOS adaptation notes (verified locally on 2026-08-28):
  - Static library (BUILD_SHARED_LIBS=OFF); SDL2IMAGE_DEPS_SHARED=OFF
    (direct linking, no dlopen); SDL2IMAGE_VENDORED=OFF (release tarball
    has no external/ submodule content).
  - E092: CMake does not know HarmonyOS; use CMAKE_SYSTEM_NAME=Linux with
    CMAKE_SYSTEM_PROCESSOR=aarch64; CMake 4.x needs CMAKE_POLICY_VERSION_MINIMUM.
  - SDL2 lookup: upstream sdl_find_sdl2 tries config mode then the private
    FindSDL2 module - inject SDL2_INCLUDE_DIR/SDL2_LIBRARY so the module
    mode works (same approach as sdl2_image 2.6.0 / sdl2_mixer 2.8.1).
  - TIFF target name: libtiff recipe exposes TIFF::tiff but upstream
    CMakeLists.txt links TIFF::TIFF; override cmake_target_name in CMakeDeps.
  - WEBP uses upstream cmake/Findwebp.cmake (module mode); CMAKE_PREFIX_PATH
    points at the libwebp package and webp_INCLUDE_PATH is set to the
    package include/ root (must contain the webp/ subdir, not include/webp).
  - libtiff/libwebp only have shared binaries (recipes hardcode
    BUILD_SHARED_LIBS=ON); SDL2_image links their .so directly. Link-time
    -L/-rpath-link resolve transitive NEEDED; runtime lookup via conanrun env.
  - Upstream test: ctest single test testimage (test/CMakeLists.txt add_test),
    SDL_VIDEODRIVER=dummy preset by TESTS_ENVIRONMENT; official CI env
    REQUIRE_LOAD_* (AVIF/JXL disabled here, matching the official Autotools
    CI scope); test binary must be ELF-signed on OHOS.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

import glob
import os
import shutil

class Sdl2ImageConan(ConanFile):
    name = "sdl2-image"
    version = "2.8.12"
    description = "SDL_image - image loading library (many formats) for SDL2"
    license = "Zlib"
    homepage = "https://github.com/libsdl-org/SDL_image"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("libtiff/4.7.2")
        self.requires("libwebp/1.6.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Upstream links TIFF::TIFF; libtiff recipe exposes TIFF::tiff. Align.
        deps.set_property("libtiff", "cmake_target_name", "TIFF::TIFF")

        # libwebp package only exposes WebP::webp (cmake_target_name), but
        # upstream SDL2_image links WebP::webpdemux too (libwebpdemux.so ships
        # in the same package). The conan toolchain sets
        # CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, so find_package(webp) hits the
        # CMakeDeps WebPConfig.cmake (single target) instead of the upstream
        # Findwebp.cmake module (which defines both targets). Inject a build
        # module that adds the missing WebP::webpdemux imported target.
        webp = self.dependencies["libwebp"]
        if webp.package_folder:
            module = os.path.join(self.generators_folder, "WebP-webpdemux.cmake")
            with open(module, "w", encoding="utf-8") as fh:
                fh.write("if(NOT TARGET WebP::webpdemux)\n")
                fh.write("  add_library(WebP::webpdemux UNKNOWN IMPORTED)\n")
                fh.write("  set_target_properties(WebP::webpdemux PROPERTIES\n")
                fh.write("      IMPORTED_LOCATION \"%s\")\n" % os.path.join(webp.package_folder, "lib", "libwebpdemux.so"))
                fh.write("endif()\n")
            deps.set_property("libwebp", "cmake_build_modules", [module])

        deps.generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # SDL2: injected find variables used when sdl_find_sdl2 falls back to
        # the private FindSDL2 module
        sdl2 = self.dependencies["sdl2"]
        if sdl2.package_folder:
            tc.cache_variables["SDL2_INCLUDE_DIR"] = os.path.join(sdl2.package_folder, "include/SDL2")
            tc.cache_variables["SDL2_LIBRARY"] = os.path.join(sdl2.package_folder, "lib/libSDL2.a")

        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["SDL2IMAGE_INSTALL"] = "ON"
        tc.variables["SDL2IMAGE_DEPS_SHARED"] = "OFF"
        tc.variables["SDL2IMAGE_VENDORED"] = "OFF"
        tc.variables["SDL2IMAGE_SAMPLES"] = "OFF"
        tc.variables["SDL2IMAGE_TESTS"] = "ON"
        tc.variables["SDL2IMAGE_TESTS_INSTALL"] = "OFF"
        tc.variables["SDL2IMAGE_TIF"] = "ON"
        tc.variables["SDL2IMAGE_WEBP"] = "ON"
        tc.variables["SDL2IMAGE_AVIF"] = "OFF"
        tc.variables["SDL2IMAGE_JXL"] = "OFF"
        tc.variables["SDL2IMAGE_BACKEND_STB"] = "ON"

        # libwebp: upstream cmake/Findwebp.cmake (module mode) needs the
        # include root that contains the webp/ subdir.
        webp = self.dependencies["libwebp"]
        if webp.package_folder:
            tc.cache_variables["webp_INCLUDE_PATH"] = os.path.join(webp.package_folder, "include")
            tc.cache_variables["webpdemux_INCLUDE_PATH"] = os.path.join(webp.package_folder, "include")

        # Shared .so transitive deps (libtiff.so -> libjpeg/zstd/z/lerc/jbig/
        # lzma/deflate/webp etc.): -L + -rpath-link resolve NEEDED at link time
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

        VirtualRunEnv(self).generate()
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

        # testimage is an executable ELF; OHOS requires code signing before run
        for tb in glob.glob(os.path.join(self.build_folder, "**", "testimage"), recursive=True):
            if os.path.isfile(tb):
                self._sign_elf(tb)

        # Upstream official test: ctest single test testimage.
        # SDL_VIDEODRIVER=dummy + SDL_TEST_SRCDIR/SDL_TEST_BUILDDIR are preset by
        # TESTS_ENVIRONMENT in test/CMakeLists.txt; add the official CI
        # REQUIRE_LOAD_* assertion env (AVIF/JXL not built here -> 0).
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_AVIF"] = "0"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_BMP"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_CUR"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_GIF"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_ICO"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_JPG"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_JXL"] = "0"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_LBM"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_PCX"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_PNG"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_PNM"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_QOI"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_SVG"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_TGA"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_TIF"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_WEBP"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_XPM"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_XV"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_SAVE_JPG"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_SAVE_PNG"] = "1"
        self.run("ctest --output-on-failure", cwd=self.build_folder,
                 env=["conanbuild", "conanrun"])

    def _sign_elf(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(oc=objcopy, f=path), ignore_errors=True)
        tmp = path + ".signed"
        self.run('{sg} sign -inFile "{f}" -outFile "{t}" -selfSign 1'.format(sg=signer, f=path, t=tmp))
        if os.path.exists(tmp):
            shutil.move(tmp, path)
        os.chmod(path, 0o755)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SDL2_image")
        self.cpp_info.set_property("cmake_target_name", "SDL2_image::SDL2_image")
        self.cpp_info.set_property("pkg_config_name", "SDL2_image")
        self.cpp_info.libs = ["SDL2_image"]
        # Static lib transitively needs SDL2 and the directly linked TIF/WEBP .so
        self.cpp_info.requires = ["sdl2::sdl2", "libtiff::libtiff", "libwebp::libwebp"]
        # IMG_webp.c also references WebPDemux* symbols from libwebpdemux.so
        # (shipped inside the libwebp package but not exposed as a component);
        # consumers of the static lib must link it explicitly.
        webp = self.dependencies["libwebp"]
        if webp.package_folder:
            webp_libdir = os.path.join(webp.package_folder, "lib")
            if webp_libdir not in self.cpp_info.libdirs:
                self.cpp_info.libdirs.append(webp_libdir)
            if "webpdemux" not in self.cpp_info.libs:
                self.cpp_info.libs.append("webpdemux")
        # Upstream installs headers into include/SDL2/; SDL_image.h does
        # #include "SDL.h", so consumers need include/SDL2 on the path
        self.cpp_info.includedirs = ["include/SDL2", "include"]
        sdl2 = self.dependencies["sdl2"]
        if sdl2.package_folder:
            self.cpp_info.includedirs.append(os.path.join(sdl2.package_folder, "include/SDL2"))
