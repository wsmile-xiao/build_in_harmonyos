#!/usr/bin/env python3
"""Conan recipe for SDL2 2.30.0 — CMake build system.

SDL2 (Simple DirectMedia Layer 2) is a cross-platform multimedia library
providing low-level access to audio, keyboard, mouse, joystick, and graphics
hardware via OpenGL/Direct3D/Metal/Vulkan.

HarmonyOS PC (OHOS) adaptations:
- SDL2 CMake does not recognize OHOS as a platform; set CMAKE_SYSTEM_NAME=Linux
  (E092) to enable Linux-like platform detection.
- Disable X11, Wayland, KMSDRM, RPI, DirectFB, Cocoa, and other platform-specific
  video/audio backends not available on OHOS.
- Enable dummy video, offscreen video, and dummy audio as fallback drivers.
- Apply patch for pthread_setcanceltype (E085 — musl does not implement POSIX
  thread cancellation API).
- SDL2 has no external dependencies (self-contained library).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SDL2Conan(ConanFile):
    name = "sdl2"
    version = "2.30.0"
    description = "Cross-platform multimedia library (audio, keyboard, mouse, joystick, graphics hardware)"
    license = "Zlib"
    homepage = "https://www.libsdl.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # SDL2 is self-contained — no external dependencies
        pass

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # R33: Do not rely on shell env vars; everything via CMake variables
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"

        # E092: Set CMAKE_SYSTEM_NAME=Linux for platform detection on OHOS
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # Disable platform-specific video/audio backends not available on OHOS
        if self.settings.os == "OHOS":
            tc.variables["SDL_X11"] = "OFF"
            tc.variables["SDL_WAYLAND"] = "OFF"
            tc.variables["SDL_KMSDRM"] = "OFF"
            tc.variables["SDL_RPI"] = "OFF"
            tc.variables["SDL_DIRECTFB"] = "OFF"
            tc.variables["SDL_COCOA"] = "OFF"
            tc.variables["SDL_VIVANTE"] = "OFF"
            tc.variables["SDL_OPENGL"] = "OFF"
            tc.variables["SDL_OPENGLES"] = "OFF"
            tc.variables["SDL_VULKAN"] = "OFF"
            tc.variables["SDL_METAL"] = "OFF"
            tc.variables["SDL_RENDER_D3D"] = "OFF"
            tc.variables["SDL_RENDER_METAL"] = "OFF"

            # Disable audio backends not available on OHOS
            tc.variables["SDL_ALSA"] = "OFF"
            tc.variables["SDL_PULSEAUDIO"] = "OFF"
            tc.variables["SDL_PIPEWIRE"] = "OFF"
            tc.variables["SDL_JACK"] = "OFF"
            tc.variables["SDL_ESD"] = "OFF"
            tc.variables["SDL_ARTS"] = "OFF"
            tc.variables["SDL_NAS"] = "OFF"
            tc.variables["SDL_SNDIO"] = "OFF"
            tc.variables["SDL_FUSIONSOUND"] = "OFF"

            # Disable joystick/haptic backends that require external libs
            tc.variables["SDL_HIDAPI"] = "OFF"

            # Enable fallback video/audio drivers
            tc.variables["SDL_DUMMYVIDEO"] = "ON"
            tc.variables["SDL_OFFSCREEN"] = "ON"

        # Disable tests and examples
        tc.variables["SDL_TESTS"] = "OFF"
        tc.variables["SDL_TEST"] = "OFF"

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
        # SDL2 provides: libSDL2.a (or libSDL2.so), libSDL2main.a
        # SDL2_test is not packaged — it is only built when SDL_TEST=ON,
        # and the CMake config files installed by SDL2 reference it.
        # Remove it from cpp_info.libs to avoid CMakeDeps errors.
        self.cpp_info.libs = ["SDL2", "SDL2main"]

        # SDL2 installs headers to include/SDL2/; set the include directory
        # so that CMakeDeps generates the correct -I path for consumers
        # using #include "SDL.h" (matching the convention of the upstream
        # SDL2 CMake config).
        self.cpp_info.includedirs = ["include/SDL2"]
        self.cpp_info.set_property("cmake_file_name", "SDL2")
        self.cpp_info.set_property("cmake_target_name", "SDL2::SDL2")
        self.cpp_info.set_property("pkg_config_name", "sdl2")

        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["pthread", "dl", "m", "rt"]
        elif self.settings.os == "OHOS":
            self.cpp_info.system_libs = ["pthread", "dl", "m"]