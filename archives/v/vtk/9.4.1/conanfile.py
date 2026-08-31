#!/usr/bin/env python3
"""Conan recipe for VTK 9.4.1 — CMake project.

VTK (Visualization Toolkit) is an open-source library for 3D computer
graphics, image processing, and visualization.  VTK 9.x builds ~150 shared
library modules under the VTK:: CMake target namespace (e.g.
VTK::CommonCore, VTK::FiltersSources).  It bundles all of its third-party
dependencies (hdf5, netcdf, freetype, zlib, jsoncpp, etc.), so this recipe
declares no requires().

This recipe:
  * Uses Conan's CMakeToolchain + CMakeDeps (R33: flags from toolchain,
    never raw CC/CXX/CFLAGS shell vars).
  * Builds shared libraries by default (BUILD_SHARED_LIBS=ON).
  * Disables testing, examples, and Python/Java wrapping.
  * Exposes the upstream-generated VTKConfig.cmake via cpp_info properties
    so consumers do `find_package(VTK COMPONENTS VTK::CommonCore ...)`.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class VtkConan(ConanFile):
    name = "vtk"
    version = "9.4.1"
    description = "VTK is an open-source library for 3D computer graphics, image processing, and visualization"
    license = "BSD-3-Clause"
    homepage = "https://vtk.org/"
    url = ""  # CI fills this

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
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # VTK bundles all third-party libraries (hdf5, netcdf, freetype,
        # zlib, jsoncpp, pugixml, libxml2, png, jpeg, tiff, lz4, lzma,
        # fmt, exprtk, fast_float, sqlite, proj, ogg, theora, eigen, etc.)
        # so no external requirements() are declared (R36: trivially
        # satisfied).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R33: All build flags come through CMakeToolchain, not raw env vars.
        # R26: honor the shared option (default ON for VTK's ~150 modules).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Disable testing, examples, and language wrappings
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        # VTK_ENABLE_WRAPPING is the master switch for all wrapping
        # infrastructure (Python, Java, serialization).  Disabling it also
        # avoids the VTKCompileTools cross-compile dependency that VTK
        # requires when CMAKE_CROSSCOMPILING=TRUE + wrapping is on
        # (see CMake/vtkCrossCompiling.cmake).
        tc.variables["VTK_ENABLE_WRAPPING"] = "OFF"
        tc.variables["VTK_WRAP_PYTHON"] = "OFF"
        tc.variables["VTK_WRAP_JAVA"] = "OFF"
        # Build the SDK headers (needed by consumers)
        tc.variables["VTK_INSTALL_SDK"] = "ON"
        # Rendering without X11: HarmonyOS PC has no X Window System.
        # VTK_USE_X defaults ON when UNIX is true (which our
        # CMAKE_SYSTEM_NAME=Linux workaround enables).  Disable it so glad
        # does not call find_package(X11) — enables headless/offscreen
        # OpenGL rendering instead.
        tc.variables["VTK_USE_X"] = "OFF"
        # ── OHOS platform workaround ──────────────────────────────────
        # The OHOS-adapted conan maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS.
        # CMake does not recognize "HarmonyOS" as a UNIX platform, so the
        # UNIX variable stays FALSE.  VTK's bundled KWSys then picks
        # ProcessWin32.c (which #includes <windows.h>) instead of
        # ProcessUNIX.c, breaking the build (E092 family).  Setting
        # CMAKE_SYSTEM_NAME=Linux makes CMake set UNIX=ON, so KWSys and
        # other platform-detection code use the correct POSIX code paths.
        # This is the established OHOS workaround (see adios2/2.12.1).
        #
        # Setting CMAKE_SYSTEM_NAME=Linux while the *host* system is
        # HarmonyOS normally makes CMake set CMAKE_CROSSCOMPILING=TRUE,
        # which breaks VTK's many try_run() configure checks (HDF5 LFS,
        # printf format, etc.) that must execute compiled test binaries.
        # Since this is a *native* build (we compile on and for the same
        # OHOS aarch64 machine), force CMAKE_CROSSCOMPILING=FALSE so
        # try_run() actually runs the test binaries on the host.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
            tc.cache_variables["CMAKE_CROSSCOMPILING"] = "FALSE"
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
        # VTK installs its OWN VTKConfig.cmake (export name "VTK") to
        # lib/cmake/vtk-9.4/, which defines the real VTK:: module targets
        # (e.g. VTK::CommonCore, VTK::FiltersSources).  Consumers use:
        #   find_package(VTK COMPONENTS VTK::CommonCore VTK::FiltersSources)
        #   target_link_libraries(myapp PRIVATE VTK::CommonCore ...)
        self.cpp_info.set_property("cmake_file_name", "VTK")
        self.cpp_info.set_property("cmake_target_name", "VTK::VTK")
        # Tell Conan NOT to generate its own VTKTargets.cmake (which would
        # only contain the single VTK::VTK target we declare here, shadowing
        # VTK's own rich VTKConfig.cmake with ~150 VTK::* module targets).
        # cmake_find_mode="none" → Conan skips CMakeDeps generation, so the
        # consumer's find_package(VTK) loads the upstream VTKConfig.cmake.
        self.cpp_info.set_property("cmake_find_mode", "none")
        # Point find_package(VTK) at the directory containing VTKConfig.cmake
        self.cpp_info.set_property("cmake_build_modules", [
            os.path.join("lib", "cmake", "vtk-9.4"),
        ])
        self.cpp_info.builddirs.append(os.path.join("lib", "cmake", "vtk-9.4"))

        # Collect all shipped VTK shared/static libraries (libvtk*.so / libvtk*.a).
        lib_dir = os.path.join(self.package_folder, "lib")
        libs = []
        if os.path.isdir(lib_dir):
            for pattern in ("libvtk*.so*", "libvtk*.a"):
                for f in glob.glob(os.path.join(lib_dir, pattern)):
                    name = os.path.basename(f)
                    # Strip lib prefix and .so*/.a suffix to get the raw lib name
                    if name.startswith("lib"):
                        name = name[3:]
                    # Remove version suffixes on shared libs (libvtkFoo.so.9.4 -> vtkFoo)
                    for suffix in (".so", ".a"):
                        idx = name.find(suffix)
                        if idx != -1:
                            name = name[:idx]
                            break
                    if name and name not in libs:
                        libs.append(name)
        if not libs:
            # Fallback so consumers at least link the aggregate namespace
            libs = ["VTK::CommonCore"]
        self.cpp_info.libs = libs

        # VTK needs pthread, dl, and math on Linux-like platforms (R32)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
