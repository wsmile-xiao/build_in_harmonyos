#!/usr/bin/env python3
"""Conan recipe for Coin3D (coin3) 4.0.7 — Open Inventor 2.1 3D visualization library.

OHOS adaptation notes (verified in R01 exploratory build):
- Primary build system is CMake (autotools also present but CMake is the 
  maintained entry point and the one used for verification).
- Required dependencies: Boost (headers; find_package(Boost REQUIRED)) and
  OpenGL (find_package(OpenGL REQUIRED)). OHOS has no desktop libGL with
  legacy immediate-mode entry points (sysroot libGLv4.so lacks glBegin/glEnd/
  glColor3f/glVertex3f/glTexCoord2f), so we depend on gl4es/1.1.6 which
  provides libGL.so translating desktop GL 1.5/2.1 fixed pipeline to GLES2.
- EGL/GLES come from the OHOS SDK sysroot (system libs). GLX/X11 are not
  available on OHOS -> COIN_BUILD_GLX=OFF, COIN_BUILD_EGL=ON.
- testsuite/TestSuiteUtils.cpp detects POSIX via _POSIX_C_SOURCE/_POSIX_SOURCE
  which the OHOS libc does not define by default -> pass
  -D_POSIX_C_SOURCE=200809L so the POSIX file-walk branch compiles.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


def _ohos_sysroot_usr():
    """Locate OHOS SDK sysroot/usr from the configured clang executable.

    clang lives at <sdk>/ohos/native/llvm/bin/clang; sysroot is
    <sdk>/ohos/native/sysroot/usr. Falls back to a list of well-known paths.
    """
    ce = os.environ.get("CONAN_TOOLCHAIN_ARGS", "")
    candidates = []
    comp = os.environ.get("CC", "")
    for cc in (comp, "/data/service/hnp/bin/clang"):
        if cc:
            real = os.path.realpath(cc)
            llvm_bin = os.path.dirname(real)
            # .../llvm/bin -> .../sysroot/usr
            cand = os.path.abspath(os.path.join(llvm_bin, "..", "..", "sysroot", "usr"))
            candidates.append(cand)
    candidates += [
        "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr",
    ]
    for c in candidates:
        if os.path.isdir(os.path.join(c, "include", "EGL")):
            return c
    raise RuntimeError(f"OHOS sysroot/usr not found (tried: {candidates})")


class Coin3Conan(ConanFile):
    name = "coin3"
    version = "4.0.7"
    description = "Coin3D — high-level 3D visualization library with Open Inventor 2.1 API"
    license = "BSD-3-Clause"
    homepage = "https://github.com/coin3d/coin"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.90.0")        # find_package(Boost REQUIRED)
        # gl4es provides libGL.so (desktop GL immediate-mode over GLES2).
        # Consume only its LIBRARY (headers=False): gl4es's GL/EGL headers
        # reference X11/Xlib.h (unavailable on OHOS), so we use the OHOS
        # sysroot headers for GL/EGL instead.
        self.requires("gl4es/1.1.6", headers=False)

    def package_id(self):
        # We only link gl4es's libGL.so; header layout changes in the
        # dependency must not invalidate this package's binary.
        pass

    def layout(self):
        # coin3 requires an out-of-source build (CMakeLists.txt rejects
        # in-source configure); cmake_layout gives a dedicated build dir.
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        sysroot_usr = _ohos_sysroot_usr()
        gl4es = self.dependencies["gl4es"].package_folder
        boost = self.dependencies["boost"].package_folder
        gl_lib = os.path.join(gl4es, "lib", "libGL.so")
        egl_lib = os.path.join(sysroot_usr, "lib", "aarch64-linux-ohos", "libEGL.so")
        # gl4es headers reference X11/Xlib.h (absent on OHOS); we link only its
        # libGL.so and use the OHOS sysroot GL/EGL headers, so drop the
        # dependency's include-dir contribution for this consumer entirely.
        self.dependencies["gl4es"].cpp_info.includedirs = []
        # CMake 4.x dropped FindBoost.cmake and the boost/1.90.0 package does
        # not ship BoostConfig.cmake, but coin3 CMakeLists calls
        # find_package(Boost REQUIRED). Provide a minimal config shim that
        # exposes the header-only Boost::boost target (coin3 only needs the
        # Boost headers), placed where Boost_DIR points.
        boost_cfg_dir = os.path.join(self.generators_folder, "boost-shim")
        os.makedirs(boost_cfg_dir, exist_ok=True)
        boost_inc = os.path.join(boost, "include")
        with open(os.path.join(boost_cfg_dir, "BoostConfig.cmake"), "w",
                  encoding="utf-8") as fh:
            fh.write(
                "set(Boost_INCLUDE_DIRS \"%s\")\n"
                "set(Boost_INCLUDE_DIR \"%s\")\n"
                "set(Boost_VERSION 109000)\n"
                "if(NOT TARGET Boost::boost)\n"
                "  add_library(Boost::boost INTERFACE IMPORTED)\n"
                "  set_target_properties(Boost::boost PROPERTIES\n"
                "    INTERFACE_INCLUDE_DIRECTORIES \"${Boost_INCLUDE_DIRS}\")\n"
                "endif()\n"
                "set(Boost_FOUND TRUE)\n" % (boost_inc, boost_inc))
        tc = CMakeToolchain(self)
        tc.cache_variables["Boost_DIR"] = boost_cfg_dir
        tc.cache_variables["COIN_BUILD_GLX"] = "OFF"     # OHOS has no X11/GLX
        tc.cache_variables["COIN_BUILD_EGL"] = "ON"
        tc.cache_variables["COIN_BUILD_TESTS"] = "ON"    # upstream unit tests
        tc.cache_variables["CMAKE_C_FLAGS"] = "-D_POSIX_C_SOURCE=200809L"
        tc.cache_variables["CMAKE_CXX_FLAGS"] = "-D_POSIX_C_SOURCE=200809L"
        # Point CMake FindOpenGL at gl4es libGL + OHOS sysroot EGL/headers.
        tc.cache_variables["OPENGL_INCLUDE_DIR"] = os.path.join(sysroot_usr, "include")
        tc.cache_variables["OPENGL_opengl_LIBRARY"] = gl_lib
        tc.cache_variables["OPENGL_gl_LIBRARY"] = gl_lib
        tc.cache_variables["OPENGL_glx_LIBRARY"] = gl_lib
        tc.cache_variables["OPENGL_glu_LIBRARY"] = gl_lib
        tc.cache_variables["OPENGL_EGL_INCLUDE_DIR"] = os.path.join(sysroot_usr, "include")
        tc.cache_variables["OPENGL_egl_LIBRARY"] = egl_lib
        # CMake does not know the HarmonyOS platform, so Platform/HarmonyOS is
        # not loaded and the -soname link flag stays empty -> the produced
        # libCoin.so would lack DT_SONAME (W3/L5 soname_gate_failed). Restore
        # the standard ELF soname flag explicitly.
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["Coin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.system_libs = ["EGL", "dl", "pthread"]
