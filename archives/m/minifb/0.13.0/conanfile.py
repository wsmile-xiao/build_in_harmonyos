#!/usr/bin/env python3
"""Conan recipe — minifb 0.13.0

MiniFB is a small cross-platform windowing framework (framebuffer
window + keyboard/mouse input). OHOS has no X11/Wayland session, so the
recipe builds the HEADLESS core with one portability patch:
- CMake recognizes HarmonyOS as a linux-like system (LINUX=TRUE) but
  keeps all window backends OFF (X11/Wayland/OpenGL) — no window
  creation, no find_package(X11) fatal;
- the linux clock_gettime timer source (its __linux__ guard is true on
  OHOS) is compiled into the core so mfb_timer_* works fully;
- mfb_open_ex/mfb_window stay intentionally undefined (documented
  headless limitation): consumers that never call mfb_open link fine —
  the usable API surface is the software framebuffer contract
  (mfb_update state machine, timers, event/key state helpers).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MiniFbConan(ConanFile):
    name = "minifb"
    version = "0.13.0"
    description = "Mini cross-platform windowing framework (headless core on OHOS)"
    license = "MIT"
    homepage = "https://github.com/emoon/minifb"
    url = "https://github.com/emoon/minifb"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "fPIC": [True, False],
        "shared": [True, False],
    }
    default_options = {
        "fPIC": True,
        "shared": False,
    }

    implements = ["auto_shared_fpic"]

    exports_sources = "patches/*", "MiniFB_ohos_stub.c"

    def layout(self):
        cmake_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # R33: flags/toolchain come from the Conan toolchain.
        tc = CMakeToolchain(self)
        tc.variables["MINIFB_BUILD_EXAMPLES"] = False
        tc.variables["MINIFB_BUILD_VERSION_INFO"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "minifb")
        self.cpp_info.set_property("cmake_target_name", "minifb::minifb")
        self.cpp_info.libs = ["minifb"]
        self.cpp_info.includedirs = ["include"]
