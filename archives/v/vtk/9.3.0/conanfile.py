#!/usr/bin/env python3
"""Conan recipe for VTK 9.3.0 — CMake project.

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
  * Runs the upstream CTest suite; disables examples and Python/Java wrapping.
  * Exposes the upstream-generated VTKConfig.cmake via cpp_info properties
    so consumers do `find_package(VTK COMPONENTS VTK::CommonCore ...)`.
"""
import os
import glob
import importlib.util
import re
import shlex
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import build_jobs


def _ohos_compiler(conanfile, lang):
    """Resolve the OHOS compiler executable from the profile conf (R33)."""
    execs = conanfile.conf.get("tools.build:compiler_executables", default={}) or {}
    return execs.get(lang) or ("clang++" if lang == "cpp" else "clang")


def _compiler_include_dirs(compiler):
    """Implicit include search dirs from `compiler -E -x c++ - -v`."""
    p = subprocess.run([compiler, "-E", "-x", "c++", "-", "-v"],
                       input="", capture_output=True, text=True, timeout=60)
    text = p.stderr + p.stdout
    m = re.search(r"#include <\.\.\.> search starts here:(.*?)End of search list\.",
                  text, re.S)
    if not m:
        return []
    return [d.strip() for d in m.group(1).splitlines() if d.strip()]


def _compiler_library_dirs(compiler):
    """Linker search dirs from `compiler -print-search-dirs`."""
    p = subprocess.run([compiler, "-print-search-dirs"],
                       capture_output=True, text=True, timeout=60)
    m = re.search(r"libraries: =(.*)", p.stdout + p.stderr)
    if not m:
        return []
    return [d for d in m.group(1).split(":") if d]


def _find_working_ninja(conanfile):
    """First ninja on PATH that actually runs.

    A stale/broken ninja earlier in PATH (e.g. a device-image copy without
    the exec bit) shadows a freshly installed one; CMake's find_program
    would pick the broken one and fail at project() with "permission
    denied" (device-verified 2026-09-05).  Walk every PATH entry and
    return the first ninja whose `--version` succeeds, so the recipe can
    pin it via CMAKE_MAKE_PROGRAM.
    """
    seen = set()
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d:
            continue
        cand = os.path.join(d, "ninja")
        if cand in seen:
            continue
        seen.add(cand)
        if not os.path.isfile(cand):
            continue
        try:
            if subprocess.run([cand, "--version"], capture_output=True,
                              timeout=30).returncode == 0:
                return cand
        except Exception:
            continue
    return None


class VtkConan(ConanFile):
    name = "vtk"
    version = "9.3.0"
    description = "VTK is an open-source library for 3D computer graphics, image processing, and visualization"
    license = "BSD-3-Clause"
    homepage = "https://vtk.org/"
    url = "https://github.com/Kitware/VTK"

    package_type = "library"
    exports_sources = "test_package/vtk_runtime.py"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "rendering": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "rendering": True,
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
        # satisfied; W0 verified with preflight_check.sh).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _runtime_helpers(self):
        path = os.path.join(self.source_folder, "test_package", "vtk_runtime.py")
        spec = importlib.util.spec_from_file_location("vtk_930_runtime", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def generate(self):
        tc = CMakeToolchain(self)
        # Ninja generator: pin a *working* ninja via CMAKE_MAKE_PROGRAM.
        # A broken ninja earlier in PATH would otherwise make CMake fail at
        # project() with "permission denied" (device-verified 2026-09-05).
        generator_conf = self.conf.get("tools.cmake.cmaketoolchain:generator",
                                       default="") or ""
        if generator_conf == "Ninja":
            ninja = _find_working_ninja(self)
            if ninja:
                tc.cache_variables["CMAKE_MAKE_PROGRAM"] = ninja
            else:
                self.output.warning("Ninja generator requested but no "
                                    "working ninja found on PATH")
        # R33: All build flags come through CMakeToolchain, not raw env vars.
        # R26: honor the shared option (default ON for VTK's ~150 modules).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # VTK's switch controls test registration; BUILD_TESTING must also
        # be ON when vtkTesting.cmake includes CTest and enables testing.
        tc.variables["VTK_BUILD_TESTING"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        if self.settings.os == "OHOS":
            # Preserve separate rounding in geometry, tick generation and
            # streamline integration/interpolation (original tests verified).
            tc.variables["VTK_ENABLE_FLOATING_POINT_CONTRACTION"] = "OFF"
        tc.cache_variables["VTK_DATA_STORE"] = os.path.join(
            self.build_folder, "ExternalData", "Objects")
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
        # Optional: disable the whole Rendering group.  Used for host
        # pre-validation on machines without X11/EGL development headers;
        # the OHOS CI/device build keeps rendering ON (default).
        if not self.options.rendering:
            tc.variables["VTK_GROUP_ENABLE_Rendering"] = "NO"
        # CMake 4.x removed compatibility with cmake_minimum_required() < 3.5
        # (hard error: "Compatibility with CMake < 3.5 has been removed").
        # VTK 9.3.0 bundles several third-party CMakeLists that still declare
        # pre-3.5 minimums (zlib 2.4.4, expat 3.1.3, pugixml 3.4, eigen 2.8.5,
        # xdmf2 2.8, xdmf3 2.8.5, ogg 2.8.12, KWIML 3.0), so the configure
        # step fails on hosts with CMake 4.x (E187).  Setting the official
        # compatibility escape CMAKE_POLICY_VERSION_MINIMUM=3.5 restores the
        # legacy tolerance without touching any upstream source (no patches).
        # It is a no-op on CMake 3.12..3.x, so it is applied unconditionally.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        #
        # Rendering backend: HarmonyOS PC has no X Window System, so
        # VTK_USE_X (default ON under the Linux system name) must be OFF.
        # Unlike VTK 9.4.1 — where vtkOpenGLOptions.cmake auto-enabled EGL
        # on "UNIX AND NOT APPLE" — VTK 9.3.0 only auto-enables EGL on
        # ANDROID/Emscripten (verified against the v9.3.0 source), so the
        # EGL/GLES offscreen backend must be enabled explicitly.  This is
        # the native HarmonyOS graphics stack (EGL + OpenGL ES), i.e. the
        # substantive platform backend — not a stub.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
            tc.cache_variables["CMAKE_CROSSCOMPILING"] = "FALSE"
            # OHOS 设备 /storage 文件系统禁止创建符号链接（设备实测：
            # cmake_symlink_library "Permission denied"，2026-09-05）。
            # 禁用版本化 SONAME → 只生成 libvtkFoo.so，零软链（CMake 官方
            # 变量，Android 平台模块同款用法）；Linux/Windows 不受影响。
            tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
            tc.cache_variables["ExternalData_NO_SYMLINKS"] = "ON"
            tc.variables["VTK_USE_X"] = "OFF"
            tc.variables["VTK_OPENGL_HAS_EGL"] = "ON"
            tc.variables["VTK_OPENGL_USE_GLES"] = "ON"
            runtime = self._runtime_helpers().create_runtime(self)
            # Keep a hash-verified object cache across rebuilds; shared-volume
            # and CMake NO_REPLACE failures are handled by stage_external_data.
            data_store = self.conf.get("user.vtk:data_store", default="") or os.path.join(
                os.path.dirname(str(runtime)), "ExternalData")
            tc.cache_variables["VTK_DATA_STORE"] = data_store
            if self.options.shared:
                tc.cache_variables["CMAKE_BUILD_RPATH"] = str(runtime)
                # DT_RPATH also resolves transitive VTK dependencies on OHOS.
                tc.extra_exelinkflags.append("-Wl,--disable-new-dtags")
            # ── OHOS EGL/GLES3 discovery fix ──────────────────────────
            # The OHOS clang resolves <EGL/egl.h> and <GLES3/gl3.h> through
            # its implicit sysroot include dirs, but CMake's find_path /
            # find_library (used by VTK's bundled FindOpenGL) does not search
            # those implicit dirs → "Could NOT find OpenGL (missing:
            # OPENGL_EGL_INCLUDE_DIR GLES3 EGL)" (device-verified 2026-09-04,
            # CMake 4.1.2).  Probe the actual compiler from the profile and
            # inject its implicit search dirs as CMake find hints
            # (CMAKE_INCLUDE_PATH / CMAKE_LIBRARY_PATH).  No SDK paths are
            # hardcoded — the same probe works on CI workers that share the
            # profile-defined toolchain (R33: everything derived from the
            # toolchain, not raw env vars).
            cxx = _ohos_compiler(self, "cpp")
            try:
                inc_dirs = _compiler_include_dirs(cxx)
                lib_dirs = _compiler_library_dirs(cxx)
                if inc_dirs:
                    tc.cache_variables["CMAKE_INCLUDE_PATH"] = ";".join(inc_dirs)
                if lib_dirs:
                    tc.cache_variables["CMAKE_LIBRARY_PATH"] = ";".join(lib_dirs)
            except Exception as exc:  # probe failure must not break configure
                self.output.warning(
                    "OHOS toolchain probe failed (%s); EGL/GLES discovery "
                    "left to CMake defaults" % exc)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        ctest = self._runtime_helpers().ctest_command(self.build_folder)
        quote = subprocess.list2cmdline if os.name == "nt" else shlex.join
        with open(os.path.join(self.build_folder, "upstream-discovery.json"),
                  "w", encoding="utf-8") as stream:
            self.run(quote([ctest, "--test-dir", self.build_folder,
                            "--show-only=json-v1"]), stdout=stream)
        if self.settings.os == "OHOS":
            self._runtime_helpers().stage_external_data(self)
        cmake.build()
        if self.settings.os == "OHOS" and self.options.shared:
            self._runtime_helpers().stage_runtime(
                self, os.path.join(self.build_folder, "lib"))
        # This is the full registered suite. Failures remain fatal to create.
        self.run(quote([ctest, "--test-dir", self.build_folder,
                        "--output-on-failure", "--no-tests=error", "--timeout", "300",
                        "--parallel", str(build_jobs(self)), "--output-junit",
                        os.path.join(self.build_folder, "upstream-tests.xml")]))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # VTK installs its OWN VTKConfig.cmake (export name "VTK") to
        # lib/cmake/vtk-9.3/, which defines the real VTK:: module targets
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
        # (VTK installs it versioned: lib/cmake/vtk-<major>.<minor>).
        vtk_cmake_dir = os.path.join(
            "lib", "cmake",
            "vtk-{}.{}".format(*self.version.split(".")[:2]),
        )
        self.cpp_info.set_property("cmake_build_modules", [vtk_cmake_dir])
        self.cpp_info.builddirs.append(vtk_cmake_dir)

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
                    # Remove version suffixes on shared libs (libvtkFoo.so.9.3 -> vtkFoo)
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
