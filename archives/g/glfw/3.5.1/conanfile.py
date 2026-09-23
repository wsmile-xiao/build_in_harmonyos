#!/usr/bin/env python3
"""Conan recipe for GLFW 3.5.1 on OHOS PC (Null-only backend).

Upstream 3.5.1 ships a Null platform (headless, no window system) that is
compiled into the core library unconditionally. This recipe keeps X11 and
Wayland disabled and relies on the Null backend plus the POSIX time/thread/
module code, so the resulting libglfw.so.3.5 works on HarmonyOS PC for API/
lifecycle level usage (glfwInitHint(GLFW_PLATFORM, GLFW_PLATFORM_NULL)).

No two-pass / bridge linking is needed: the upstream core library has no
circular .so dependency (unlike the ohos_native_glfw fork used for 3.4.6).

OHOS specifics handled here:
- posix_time.c needs <time.h> (musl + strict c99 hides CLOCK_* constants);
  plus _DEFAULT_SOURCE via CFLAGS, mirroring upstream's Linux workaround
  (src/CMakeLists.txt only adds it when CMAKE_SYSTEM_NAME == "Linux", which
  is not the case for the OHOS toolchain).
- The Conan CMakeToolchain would map os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS
  (unknown platform, no SONAME support). We self-discover the OHOS NDK
  ohos.toolchain.cmake instead so SONAME + versioned symlinks are emitted.
- EGL/GLES context support stays code-only (runtime dlopen, see
  egl_context.c soname tables): the Null-only package links nothing beyond
  libc, so _GLFW_EGL_LIBRARY/_GLFW_GLESV2_LIBRARY are NOT injected; OHOS
  users with versioned-soname issues can add them later if needed.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class GlfwConan(ConanFile):
    name = "glfw"
    version = "3.5.1"
    description = "A multi-platform library for OpenGL, OpenGL ES, Vulkan, window and input"
    license = "Zlib"
    homepage = "https://www.glfw.org/"
    url = "https://github.com/glfw/glfw"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # no third-party requirements: Null backend needs only libc

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
        # Self-discover the OHOS NDK ohos.toolchain.cmake so the recipe does
        # not depend on the profile [conf] user_toolchain entry:
        # 1) profile [conf] tools.cmake.cmaketoolchain:user_toolchain
        # 2) OHOS_NDK_HOME environment variable
        # 3) glob the on-device / CI SDK layout
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        candidates = list(ut)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        if ndk:
            candidates.append(os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake"))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "ohos.toolchain.cmake not found: set OHOS_NDK_HOME or configure "
            "tools.cmake.cmaketoolchain:user_toolchain in the profile [conf]")

    def build(self):
        if str(self.settings.os) == "OHOS":
            # See module docstring: use the NDK toolchain directly for
            # CMAKE_SYSTEM_NAME=OHOS (SONAME + versioned symlinks) instead of
            # the Conan generated conan_toolchain.cmake (unknown platform).
            toolchain = self._ohos_toolchain()
            self.run(
                'cmake -B "{}" -S "{}" -DCMAKE_TOOLCHAIN_FILE="{}" '
                "-DOHOS_ARCH=arm64-v8a -DCMAKE_BUILD_TYPE={} "
                "-DGLFW_BUILD_X11=OFF -DGLFW_BUILD_WAYLAND=OFF "
                "-DGLFW_BUILD_EXAMPLES=OFF -DGLFW_BUILD_TESTS=OFF "
                "-DGLFW_BUILD_DOCS=OFF -DBUILD_SHARED_LIBS={} "
                '-DGLFW_LIBRARY_TYPE={} -DCMAKE_C_FLAGS="-D_DEFAULT_SOURCE" '
                '-DCMAKE_CXX_FLAGS="-D_DEFAULT_SOURCE" '
                '-DCMAKE_SHARED_LINKER_FLAGS="-Wl,--undefined-version"'.format(
                    self.build_folder,
                    self.source_folder,
                    toolchain,
                    self.settings.build_type,
                    "ON" if self.options.shared else "OFF",
                    "SHARED" if self.options.shared else "STATIC",
                )
            )
            self.run('cmake --build "{}" --parallel 2'.format(self.build_folder))
        else:
            from conan.tools.cmake import CMake, CMakeToolchain

            tc = CMakeToolchain(self)
            tc.variables["GLFW_BUILD_X11"] = False
            tc.variables["GLFW_BUILD_WAYLAND"] = False
            tc.variables["GLFW_BUILD_EXAMPLES"] = False
            tc.variables["GLFW_BUILD_TESTS"] = False
            tc.variables["GLFW_BUILD_DOCS"] = False
            tc.generate()
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def package(self):
        if str(self.settings.os) == "OHOS":
            self.run('cmake --install "{}" --prefix "{}"'.format(self.build_folder, self.package_folder))
        else:
            from conan.tools.cmake import CMake

            CMake(self).install()
        # headers + cmake/pkg-config files are installed by the root project's
        # install(TARGETS glfw EXPORT glfwTargets) and install(EXPORT...) rules

    def package_info(self):
        self.cpp_info.libs = ["glfw"]
        self.cpp_info.set_property("cmake_file_name", "glfw3")
        self.cpp_info.set_property("cmake_target_name", "glfw::glfw")
        self.cpp_info.set_property("pkg_config_name", "glfw3")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "rt", "dl"]
