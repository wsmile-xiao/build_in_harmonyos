"""Conan recipe for AIDA-X 1.1.0 (AidaDSP Amp Model Player).

Build system: CMake (DPF - DISTRHO Plugin Framework).
HarmonyOS adaptation: OpenGL UI removed (platform has no OpenGL/GLX/EGL),
plugin builds headless (DSP-only) producing CLAP/LV2/VST2/VST3 + standalone.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AidaXConan(ConanFile):
    name = "aida"
    version = "1.1.0"
    description = "AIDA-X - Amp Model Player leveraging AI (DSP-only, headless build for HarmonyOS)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/AidaDSP/AIDA-X"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        # Explicitly export the patch file alongside conandata
        export_conandata_patches(self)
        copy(self, "patches/*.patch", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        # All dependencies (dpf, rtneural, FFTConvolver, r8brain) are embedded
        # as git submodules in the release tarball. No external Conan requires.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # rtneural ships cmake_minimum_required(VERSION 2.x) which CMake 4.x rejects
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # HarmonyOS platform: tell DPF the target arch (DPF VST3 packaging needs it)
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # DPF internal config
        tc.variables["RTNEURAL_XSIMD"] = False
        tc.generate()

    def build(self):
        # Apply HarmonyOS adaptation patch (remove OpenGL UI)
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # DPF has no install target; stage artifacts manually
        bin_dir = os.path.join(self.build_folder, "bin")
        # Standalone executable
        copy(self, "AIDA-X", src=bin_dir, dst=os.path.join(self.package_folder, "bin"))
        # Plugin formats
        copy(self, "AIDA-X.clap", src=bin_dir, dst=os.path.join(self.package_folder, "lib", "clap"))
        copy(self, "AIDA-X-vst2.so", src=bin_dir, dst=os.path.join(self.package_folder, "lib", "vst2"))
        copy(self, "*", src=os.path.join(bin_dir, "AIDA-X.lv2"), dst=os.path.join(self.package_folder, "lib", "lv2", "AIDA-X.lv2"))
        copy(self, "*", src=os.path.join(bin_dir, "AIDA-X.vst3"), dst=os.path.join(self.package_folder, "lib", "vst3", "AIDA-X.vst3"))
        # Static DSP libraries (for consumer linking via cpp_info.libs)
        # In Conan 2.x, self.build_folder is already b/build/Release/
        # so the .a files are directly in self.build_folder
        copy(self, "*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        # Plugin library - consumers link against the DSP core
        self.cpp_info.libs = ["AIDA-X-dsp", "AIDA-X-Standalone-dsp"]
        # AIDA-X is a plugin (no public headers for consumers);
        # clear includedirs to avoid referencing non-existent include/
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
