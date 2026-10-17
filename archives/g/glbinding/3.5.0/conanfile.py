#!/usr/bin/env python3
"""Conan recipe for glbinding 3.5.0 on OHOS PC (aarch64).

glbinding is a CMake-based C++ binding for the OpenGL API, generated from the
Khronos OpenGL XML specification. The upstream tarball ships pre-generated
binding sources (source/glbinding/source/gl/*.cpp), so no code generation is
needed at build time.

OHOS build notes (mirrors the proven glfw 3.5.1 recipe pattern):
- Self-discover the OHOS NDK ohos.toolchain.cmake and drive cmake with it
  directly (CMAKE_SYSTEM_NAME=OHOS), instead of the Conan CMakeToolchain whose
  os=OHOS -> CMAKE_SYSTEM_NAME=HarmonyOS mapping is an unknown platform to CMake.
- Pass every glbinding option as an explicit -D on the command line: the
  upstream root CMakeLists declares `option(BUILD_SHARED_LIBS ... ON)` and
  `option(OPTION_BUILD_TOOLS ... ON)`, which override cache/toolchain variables
  under CMP0077 NEW on newer CMake; command-line -D always wins.
- The OHOS SDK llvm/bin ships llvm-ar but NO llvm-ranlib; use the on-device
  /data/service/hnp/bin/llvm-ranlib symlink (which resolves to llvm-ar) so
  static library archiving succeeds.
- OPTION_BUILD_TOOLS=OFF / OPTION_BUILD_EXAMPLES=OFF: upstream tools (glinfo,
  glmeta, ...) require glfw3 + a live GL/EGL context and are not part of the
  library deliverable on a headless OHOS build. Package type is library only,
  so no commands.json is required (R38: "库类型不需要"; PF8: pure-library
  packages must NOT carry commands.json).
- OPTION_BUILD_TESTS=OFF in the recipe: upstream tests are enumerated and run
  separately in the adaptation flow (they require googletest from the registry);
  the conan L1 smoke test lives in test_package/.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class GlbindingConan(ConanFile):
    name = "glbinding"
    version = "3.5.0"
    description = "A C++ binding for the OpenGL API, generated from the Khronos OpenGL XML specification"
    license = "MIT"
    homepage = "https://github.com/cginternals/glbinding"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No third-party requires: the core library needs only libc/libdl.
        pass

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
        """Self-discover the OHOS NDK ohos.toolchain.cmake (glfw 3.5.1 pattern)."""
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

    def _ohos_cmake_args(self):
        toolchain = self._ohos_toolchain()
        args = [
            f'-B "{self.build_folder}" -S "{self.source_folder}"',
            f'-DCMAKE_TOOLCHAIN_FILE="{toolchain}"',
            "-DOHOS_ARCH=arm64-v8a",
            f"-DCMAKE_BUILD_TYPE={self.settings.build_type}",
            "-DBUILD_SHARED_LIBS=" + ("ON" if self.options.shared else "OFF"),
            "-DOPTION_BUILD_TOOLS=OFF",
            "-DOPTION_BUILD_EXAMPLES=OFF",
            "-DOPTION_BUILD_TESTS=OFF",
            "-DOPTION_BUILD_DOCS=OFF",
            "-DOPTION_BUILD_OWN_KHR_HEADERS=ON",
            "-DOPTION_USE_GIT_INFORMATION=OFF",
            "-DGLBINDING_BUILD_AS_ROOT=ON",
            "-DCMAKE_AR=/data/service/hnp/bin/llvm-ar",
            "-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib",
        ]
        return args

    def build(self):
        if str(self.settings.os) == "OHOS":
            args = self._ohos_cmake_args()
            self.run("cmake " + " ".join(args))
            self.run('cmake --build "{}" --parallel 2'.format(self.build_folder))
        else:
            from conan.tools.cmake import CMake, CMakeToolchain

            tc = CMakeToolchain(self)
            tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
            tc.variables["OPTION_BUILD_TOOLS"] = "OFF"
            tc.variables["OPTION_BUILD_EXAMPLES"] = "OFF"
            tc.variables["OPTION_BUILD_TESTS"] = "OFF"
            tc.variables["OPTION_BUILD_DOCS"] = "OFF"
            tc.variables["OPTION_BUILD_OWN_KHR_HEADERS"] = "ON"
            tc.variables["OPTION_USE_GIT_INFORMATION"] = "OFF"
            tc.variables["GLBINDING_BUILD_AS_ROOT"] = "ON"
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

    def package_info(self):
        self.cpp_info.libs = ["glbinding", "glbinding-aux"]
        self.cpp_info.set_property("cmake_file_name", "glbinding")
        self.cpp_info.set_property("cmake_target_name", "glbinding::glbinding")
        self.cpp_info.set_property("pkg_config_name", "glbinding")
        if self.settings.os in ("Linux", "OHOS"):
            # getProcAddress.cpp uses dlopen/dlsym at runtime
            self.cpp_info.system_libs = ["dl"]
