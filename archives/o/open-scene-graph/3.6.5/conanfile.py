#!/usr/bin/env python3
"""Conan recipe - open-scene-graph 3.6.5 (OpenSceneGraph 3D graphics toolkit).

Upstream: https://github.com/openscenegraph/OpenSceneGraph (tag
OpenSceneGraph-3.6.5). CMake build system, C++.

OHOS PC adaptation (GLES3 profile, headless):
  - OpenGL profile is GLES3 (no desktop GL on OHOS PC): OPENGL_PROFILE=GLES3
    with OSG_GLES3_AVAILABLE=ON and every other GL variant (GL1/GL2/GL3/
    GLES1/GLES2 + fixed-function/displaylists/matrices/vertex funcs) OFF.
  - OSG_WINDOWING_SYSTEM=None: no X11/Wayland on OHOS; osgViewer builds the
    headless GraphicsWindow base only (3D rendering requires a graphics
    context provided by the consumer, e.g. EGL via system libEGL/libGLESv3).
  - OpenGL/EGL discovery: upstream CMakeLists does FIND_PACKAGE(OpenGL) /
    FIND_PACKAGE(EGL) with its own FindEGL.cmake. The OHOS SDK sysroot ships
    GLES3/EGL headers (usr/include/GLES3, usr/include/EGL) and stub .so
    (usr/lib/aarch64-linux-ohos/libGLESv3.so, libEGL.so), but no desktop GL.
    We inject OPENGL_INCLUDE_DIR / OPENGL_gl_LIBRARY / EGL_LIBRARY /
    EGL_INCLUDE_DIR directly (same approach as the 2026-06 native build
    notes and the glfw 3.5.1 recipe).
  - E092: CMake does not know HarmonyOS; build with CMAKE_SYSTEM_NAME=Linux
    + CMAKE_SYSTEM_PROCESSOR=aarch64 so IF(UNIX) branches work. The
    OpenThreads pthreads backend is then selected through the plain UNIX
    path; patch 0001 keeps a HarmonyOS fallback for native builds.
  - CMake >= 3.27 policy: upstream cmake_minimum_required(2.6/2.8) needs
    CMAKE_POLICY_VERSION_MINIMUM=3.5.
  - Third-party plugins: upstream skips a plugin when its FIND_PACKAGE
    result stays NOT FOUND, so every optional third-party library
    (freetype/jpeg/png/tiff/curl/giflib/sdl2/rsvg/...) is force-set to
    NOTFOUND. The recipe is therefore dependency-free (task W0 verified)
    and builds the core libs plus the dependency-free plugins.
  - musl libc: pthread_cancel/pthread_testcancel/pthread_setcancelstate are
    not implemented; upstream pthreads CMakeLists defines HAVE_PTHREAD_*
    unconditionally - patched via CHECK_FUNCTION_EXISTS (0002). sys/unistd.h
    does not exist - replaced by unistd.h (0003). OpenThreads UNIX guard
    gets a HarmonyOS fallback (0001, harmless under Linux system name).
  - Upstream tests: source audit of the 3.6.5 tarball shows ZERO ctest
    registrations (no add_test/enable_testing anywhere; CTestConfig.cmake
    only configures a CDash dashboard that is never fed). Upstream
    "testing" is the examples/ suite (BUILD_OSG_EXAMPLES, default OFF),
    which consists of interactive GPU demos requiring a display server -
    not runnable on headless CI (verified on 2026-06 native build:
    "make check: no automated tests"). Therefore N (upstream registered
    test targets) = 0; nothing to run or exempt item-by-item. Consumer
    validation is done by test_package (links libosg + runs osgversion).
"""
import glob
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class OpenSceneGraphConan(ConanFile):
    name = "open-scene-graph"
    version = "3.6.5"
    description = "OpenSceneGraph - open source high performance 3D graphics toolkit"
    license = "LGPL-2.1-only WITH WxWindows-exception-3.1"
    homepage = "https://github.com/openscenegraph/OpenSceneGraph"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_applications": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "build_applications": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Dependency-free core: GL/EGL headers and stub libs come from the
        # OHOS SDK sysroot; every third-party plugin dependency is disabled
        # (see module docstring). No conan requires.
        pass

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"open-scene-graph only supports Linux/OHOS, got: {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"OHOS builds require armv8/aarch64, got: {self.settings.arch}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sysroot(self):
        # OHOS SDK sysroot with GLES3/EGL headers + stub libs. On CI the
        # same /data/service/hnp layout is present (see CI profile PATH).
        globbed = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot"))
        if not globbed:
            raise ConanInvalidConfiguration(
                "OHOS SDK sysroot not found under /data/service/hnp/ohos-sdk.org")
        return globbed[-1]

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: build as Linux/aarch64 - upstream CMake pre-dates HarmonyOS
        # and its IF(UNIX)/IF(APPLE)/IF(WIN32) branches must resolve the
        # unix/pthreads path (matching the E092 SDL2_image approach).
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # OHOS worker /bin/sh is execute-only: skip compiler try-compile.
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "TRUE"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "TRUE"
        # CheckAtomicOps.cmake try_run()s the GCC __atomic builtins test;
        # in cross-compiling mode try_run cannot execute the binary, so we
        # pre-seed the expected exit code (clang aarch64 fully supports the
        # __atomic builtins - same approach as examples/osgemscripten).
        tc.cache_variables["_OPENTHREADS_ATOMIC_USE_GCC_BUILTINS_EXITCODE"] = "0"
        tc.cache_variables["_OPENTHREADS_ATOMIC_USE_GCC_BUILTINS_EXITCODE__TRYRUN_OUTPUT"] = ""

        if str(self.settings.os) == "OHOS":
            sysroot = self._sysroot()
            inc = os.path.join(sysroot, "usr", "include")
            libdir = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
            gles3 = os.path.join(libdir, "libGLESv3.so")
            egl = os.path.join(libdir, "libEGL.so")
            # Upstream: LINK_CORELIB_DEFAULT uses OPENGL_gl_LIBRARY + EGL_LIBRARY
            tc.cache_variables["OPENGL_INCLUDE_DIR"] = inc
            tc.cache_variables["OPENGL_gl_LIBRARY"] = gles3
            tc.cache_variables["OPENGL_opengl_LIBRARY"] = gles3
            tc.cache_variables["OPENGL_glesv2_LIBRARY"] = gles3
            tc.cache_variables["EGL_INCLUDE_DIR"] = inc
            tc.cache_variables["EGL_LIBRARY"] = egl
            # Third-party plugin deps: disable their find_package() calls
            # entirely. A plain NOTFOUND value only covers the module-mode
            # result variables; on CI workers a stale config-mode package
            # (e.g. ~/usr/local/lib/cmake/freetype referencing a deleted
            # libfreetype.a) would still be picked up and fail. Setting
            # CMAKE_DISABLE_FIND_PACKAGE_<Pkg> makes find_package treat the
            # package as not found, so upstream skips the matching plugins
            # (keeps this recipe dependency-free).
            for pkg in ("Freetype", "ilmbase", "Inventor", "Jasper", "OpenEXR",
                        "OpenCascade", "COLLADA", "FBX", "ZLIB", "GDAL", "GTA",
                        "CURL", "LibVNCServer", "DCMTK", "FFmpeg", "GStreamer",
                        "GLIB", "DirectShow", "SDL2", "SDL", "Poppler-glib",
                        "RSVG", "GtkGl", "DirectInput", "NVTT", "Asio",
                        "ZeroConf", "LIBLAS", "Lua52", "Lua51", "GIFLIB",
                        "JPEG", "PNG", "TIFF"):
                tc.cache_variables[f"CMAKE_DISABLE_FIND_PACKAGE_{pkg}"] = True
            tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_X11"] = True

        # GLES3-only profile (see module docstring).
        tc.variables["OPENGL_PROFILE"] = "GLES3"
        tc.variables["OSG_GLES3_AVAILABLE"] = True
        tc.variables["OSG_GL1_AVAILABLE"] = False
        tc.variables["OSG_GL2_AVAILABLE"] = False
        tc.variables["OSG_GL3_AVAILABLE"] = False
        tc.variables["OSG_GLES1_AVAILABLE"] = False
        tc.variables["OSG_GLES2_AVAILABLE"] = False
        tc.variables["OSG_GL_FIXED_FUNCTION_AVAILABLE"] = False
        tc.variables["OSG_GL_DISPLAYLISTS_AVAILABLE"] = False
        tc.variables["OSG_GL_MATRICES_AVAILABLE"] = False
        tc.variables["OSG_GL_VERTEX_FUNCS_AVAILABLE"] = False
        tc.variables["OSG_GL_VERTEX_ARRAY_FUNCS_AVAILABLE"] = False
        tc.variables["OSG_WINDOWING_SYSTEM"] = "None"
        # No interactive examples (they are the "upstream test suite" but
        # need a GPU/display, unavailable in CI; see module docstring).
        tc.variables["BUILD_OSG_EXAMPLES"] = False
        tc.variables["BUILD_OSG_APPLICATIONS"] = bool(self.options.build_applications)
        tc.variables["BUILD_OSG_PLUGINS"] = True
        # musl: no fontconfig on OHOS CI.
        tc.variables["OSG_TEXT_USE_FONTCONFIG"] = False
        # Shared libraries with SONAMEs (default upstream on Linux).
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # The bundled cfg plugin lex/yacc generated sources use the removed
        # C++17 'register' storage class; clang turns -Wregister into an
        # error under upstream's -Wall -pedantic. Downgrade it to ignored.
        tc.variables["CMAKE_CXX_FLAGS"] = "-Wno-register"
        # CMake's install-time RPATH rewrite (file(RPATH_CHANGE), the
        # "Set non-toolchain portion of runtime path ... to """ step)
        # corrupts the ELF files on the HMDFS-backed conan cache: the
        # rewritten .so cannot be loaded by the musl dynamic loader any
        # more (verified: build-tree copy loads, installed copy fails).
        # Building with the (empty) install RPATH from the start makes
        # `cmake --install` a plain copy with no ELF rewrite. Consumers
        # resolve the SONAMEs through LD_LIBRARY_PATH / conanrun anyway.
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["CMAKE_INSTALL_RPATH"] = ""
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # OHOS worker: /bin/sh is execute-only, GNU make fails to stat it;
        # Ninja does not. Keep parallelism low to avoid OOM on big plugins.
        cmake.build(cli_args=["--parallel", "2"])
        # Upstream registered ctest targets: 0 (source audit, see module
        # docstring). Emit the evidence marker for the CI L1 harness.
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "passed",
            "framework": "ctest",
            "command": "ctest (no tests registered upstream)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "OpenSceneGraph 3.6.5 has no add_test/enable_testing "
                      "registrations; examples/ are interactive GPU demos "
                      "(BUILD_OSG_EXAMPLES=OFF, headless CI)",
        }))
        # Smoke-run the just-built osgversion binary (prints the version
        # string; links core libs only, no graphics context needed).
        osgversion = os.path.join(self.build_folder, "bin", "osgversion")
        if os.path.isfile(osgversion) and str(self.settings.os) == "OHOS":
            self._sign_elf(osgversion)
            # The binary needs libc++ from the OHOS SDK (same layout the CI
            # profile puts on LD_LIBRARY_PATH) plus the fresh build libs.
            # Runtime library resolution order (verified on device):
            # /system/lib64 first (system libEGL/libhilog need the system
            # libc++.so), then the build-tree libs (libosg*.so.3.6.5), then
            # the NDK per-arch libc++_shared.so dir.
            parts = [
                "/system/lib64",
                os.path.join(self.build_folder, "lib"),
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
            ]
            llp = os.environ.get("LD_LIBRARY_PATH", "")
            for d in llp.split(":"):
                if d and d not in parts:
                    parts.append(d)
            os.environ["LD_LIBRARY_PATH"] = ":".join(parts)
            self.run(f'"{osgversion}"')
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": True, "passed": True, "command": "osgversion",
                "discovered": 1, "passedCount": 1,
            }))

    def _sign_elf(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(
            oc=objcopy, f=path), ignore_errors=True)
        tmp = path + ".signed"
        self.run('{sg} sign -inFile "{f}" -outFile "{t}" -selfSign 1'.format(
            sg=signer, f=path, t=tmp))
        if os.path.exists(tmp):
            shutil.move(tmp, path)
        os.chmod(path, 0o755)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Core libraries installed by upstream (GLES3 profile, no optional
        # third-party deps). Order matches upstream link order expectations.
        self.cpp_info.libs = [
            "osgPresentation", "osgWidget", "osgUI", "osgManipulator",
            "osgVolume", "osgFX", "osgShadow", "osgSim", "osgTerrain",
            "osgParticle", "osgText", "osgViewer", "osgGA", "osgUtil",
            "osgDB", "osgAnimation", "osg", "OpenThreads",
        ]
        self.cpp_info.set_property("cmake_file_name", "OpenSceneGraph")
        self.cpp_info.set_property("cmake_target_name", "OpenSceneGraph::OpenSceneGraph")
        self.cpp_info.set_property("pkg_config_name", "openscenegraph")
        self.cpp_info.set_property("pkg_config_aliases", ["osg", "openscenegraph"])
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
        if str(self.settings.os) == "OHOS":
            # GL/EGL are runtime-loaded system libs on the device.
            self.cpp_info.system_libs += ["EGL", "GLESv3"]
