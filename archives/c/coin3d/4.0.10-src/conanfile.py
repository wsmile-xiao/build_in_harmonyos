#!/usr/bin/env python3
"""Conan recipe for Coin3D 4.0.10-src on OHOS PC.

Coin3D implements the Open Inventor 3D graphics API on top of desktop
OpenGL. OHOS ships only OpenGL ES, so desktop-GL linkage is provided by the
registry mesa/24.3.4.1 package: its libOSMesa exports the full desktop-GL
entry points (software rendering) and installs desktop GL headers.

Platform handling:
- X11/GLX/EGL code paths are compiled out (COIN_BUILD_GLX/COIN_BUILD_EGL
  =OFF) so find_package(X11 REQUIRED) is never reached; Coin itself never
  creates windows or GL contexts -- applications supply them (OSMesa
  offscreen contexts, or EGL + gl4es).
- Upstream runtime-linking switches: Freetype/ZLib/BZip2/OpenAL are moved
  to compile-time linkage against Conan dependencies; GLU and FontConfig
  keep upstream dlopen-with-graceful-degradation (no libGLU/libfontconfig
  on OHOS: GLU-dependent rendering degrades, documented limitation).
- USE_SUPERGLU=OFF (no superglu in the registry; with platform GLU absent
  HAVE_GLU stays undefined and Coin uses its internal fallbacks).
- expat stays bundled upstream (USE_EXTERNAL_EXPAT=OFF default).
- The upstream test suite (testsuite/: COIN_TEST_SUITE blocks extracted
  from library sources into one CoinTests binary registered via add_test,
  plus models/*.iv file regressions) is built and executed with ctest
  inside build().

Toolchain note (same approach as archives/g/glfw/3.5.1): the recipe
self-discovers the OHOS NDK ohos.toolchain.cmake so the build gets
CMAKE_SYSTEM_NAME=OHOS with SONAME support.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Coin3DConan(ConanFile):
    name = "coin3d"
    version = "4.0.10-src"
    description = "Coin3D - full-featured Open Inventor implementation"
    license = "BSD-3-Clause"
    homepage = "https://github.com/coin3d/coin"
    url = "https://github.com/coin3d/coin"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("mesa/24.3.4.1")       # desktop GL headers + libOSMesa (GL symbols)
        self.requires("freetype/2.14.3")     # 3D font rendering
        self.requires("zlib/1.3.1")          # compressed scenes (.iv.gz / .wrl.gz)
        self.requires("bzip2/1.0.8")         # compressed sound files
        self.requires("openal/1.25.2")       # HAVE_SOUND sound rendering

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain",
                           default=[], check_type=list)
        candidates = list(ut)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        if ndk:
            candidates.append(os.path.join(ndk, "build", "cmake",
                                           "ohos.toolchain.cmake"))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/"
            "ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "ohos.toolchain.cmake not found: set OHOS_NDK_HOME or configure "
            "tools.cmake.cmaketoolchain:user_toolchain in the profile [conf]")

    def build(self):
        d = self.dependencies
        deps = ("mesa", "freetype", "zlib", "bzip2", "openal")
        prefix_paths = ";".join(d[n].package_folder for n in deps)
        lib_dirs = ":".join(
            os.path.join(d[n].package_folder, "lib") for n in deps)
        mesa_pkg = d["mesa"].package_folder
        gl_lib = os.path.join(mesa_pkg, "lib", "libOSMesa.so")
        toolchain = self._ohos_toolchain()
        shared = "ON" if self.options.shared else "OFF"
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            "-DCOIN_BUILD_SHARED_LIBS=%s" % shared,
            "-DCOIN_BUILD_TESTS=ON",
            "-DCOIN_BUILD_EXAMPLES=OFF",
            "-DCOIN_BUILD_DOCUMENTATION=OFF",
            "-DCOIN_BUILD_GLX=OFF",
            "-DCOIN_BUILD_EGL=OFF",
            "-DUSE_SUPERGLU=OFF",
            "-DUSE_EXTERNAL_EXPAT=OFF",
            "-DFREETYPE_RUNTIME_LINKING=OFF",
            "-DZLIB_RUNTIME_LINKING=OFF",
            "-DLIBBZIP2_RUNTIME_LINKING=OFF",
            "-DOPENAL_RUNTIME_LINKING=OFF",
            '-DCMAKE_PREFIX_PATH="%s"' % prefix_paths,
            '-DOPENGL_INCLUDE_DIR="%s"' % os.path.join(mesa_pkg, "include"),
            '-DOPENGL_gl_LIBRARY="%s"' % gl_lib,
            '-DOPENGL_opengl_LIBRARY="%s"' % gl_lib,
            '-DCMAKE_SHARED_LINKER_FLAGS="-Wl,--undefined-version"',
            # testsuite/TestSuiteUtils.cpp keys its POSIX/WIN32 switch on
            # _POSIX_C_SOURCE/_POSIX_SOURCE, which musl+clang does not
            # predefine before that check -- select the POSIX branch (the
            # helper only uses opendir/readdir).
            '-DCMAKE_C_FLAGS="-D_POSIX_C_SOURCE=200809L"',
            '-DCMAKE_CXX_FLAGS="-D_POSIX_C_SOURCE=200809L"',
        ]
        self.run('cmake -B "%s" -S "%s" %s' % (
            self.build_folder, self.source_folder, " ".join(defs)))
        self.run('cmake --build "%s" --parallel 2' % self.build_folder)
        # Upstream test suite must actually execute (CoinTests via add_test).
        self.run('LD_LIBRARY_PATH="%s" ctest --test-dir "%s" '
                 '--output-on-failure' % (lib_dirs, self.build_folder))

    def package(self):
        self.run('cmake --install "%s" --prefix "%s"' % (
            self.build_folder, self.package_folder))
        # cmake --install rewrites the installed ELF (install RPATH removal
        # pass), producing a file musl's strict loader refuses to load even
        # though the byte-different build-tree copy loads fine -- ship the
        # unmodified build-tree library instead.
        src = os.path.join(self.build_folder, "lib")
        dst = os.path.join(self.package_folder, "lib")
        for name in ("libCoin.so", "libCoin.so.80", "libCoin.so.80.0.10"):
            f = os.path.join(src, name)
            if os.path.isfile(f):
                shutil.copyfile(f, os.path.join(dst, name))

    def package_info(self):
        self.cpp_info.libs = ["Coin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "coin3d")
        self.cpp_info.set_property("cmake_target_name", "coin3d::coin3d")
