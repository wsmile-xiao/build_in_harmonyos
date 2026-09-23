#!/usr/bin/env python3
"""Conan recipe for tracy 0.13.1 — HarmonyOS (OpenHarmony PC) aarch64 adaptation.

Tracy is a frame profiler. This recipe packages the **client library**
(`TracyClient`), which upstream builds from the single translation unit
`public/TracyClient.cpp`. The profiler GUI lives in the separate `profiler/`
CMake project and is not part of the root CMakeLists.txt, so the default build
is already GUI-free (no GLFW/X11/Wayland requirement).

Portability notes for OHOS:
  - The root CMakeLists guards platform-specific extras: `execinfo` is only
    required on FreeBSD and `libunwind`/`debuginfod`/`rocprofiler-sdk` are
    optional (OFF by default), so no extra system library is needed.
  - `find_package(Threads REQUIRED)` is satisfied by the OHOS sysroot
    (`libpthread.a`); `CMAKE_DL_LIBS` resolves to `libdl.a`. Both are exported
    as system libs below so static consumers do not have to add them by hand.
  - Upstream installs the public headers as
    `<prefix>/include/tracy/{tracy,client,common}/...` and declares
    `INSTALL_INTERFACE include/tracy`, therefore consumers include
    `#include <tracy/TracyC.h>` with `includedirs = ["include/tracy"]`.
  - `TRACY_ENABLE` is a PUBLIC compile definition upstream. It must reach
    consumers: without it `TracyC.h` (#ifndef TRACY_ENABLE) degrades the whole
    API to no-op macros, so it is exported through `cpp_info.defines`.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class TracyConan(ConanFile):
    name = "tracy"
    version = "0.13.1"
    description = "Frame profiler — the Tracy client library (TracyClient)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/wolfpld/tracy"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is adapted for Linux/OHOS only (got os={self.settings.os})"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Static client by default; shared is opt-in through -o shared=True.
        tc.variables["TRACY_STATIC"] = not bool(self.options.shared)
        # Profiling must be compiled in, otherwise the client is a no-op.
        tc.variables["TRACY_ENABLE"] = True
        # Keep the build surface minimal on OHOS: no Fortran bindings, no LTO,
        # no Python client (the latter would pull in pybind11 and require a
        # shared client).
        tc.variables["TRACY_Fortran"] = False
        tc.variables["TRACY_LTO"] = False
        tc.variables["TRACY_CLIENT_PYTHON"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["TracyClient"]
        self.cpp_info.includedirs = ["include/tracy"]
        self.cpp_info.defines = ["TRACY_ENABLE"]
        # Mirrors upstream target_link_libraries(TracyClient PUBLIC
        # Threads::Threads ${CMAKE_DL_LIBS}).
        self.cpp_info.system_libs = ["pthread", "dl"]
        self.cpp_info.set_property("pkg_config_name", "tracy")
