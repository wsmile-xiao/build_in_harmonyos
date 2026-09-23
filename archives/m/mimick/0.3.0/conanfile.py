from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os


class MimickConan(ConanFile):
    name = "mimick"
    version = "0.3.0"
    description = "A portable C mocking library"
    license = "MIT"
    homepage = "https://github.com/Snaipe/Mimick"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Mimick's ELF implementation expects a Linux-like executable format.
        # The actual binary is still built with the target OHOS compiler.
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["USE_QEMU"] = "OFF"
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # On OHOS AArch64 Clang this avoids emulated-TLS re-entering a mocked
        # allocator while the trampoline is resolving thread-local state.
        tc.variables["CMAKE_C_FLAGS"] = "-fno-emulated-tls"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            "CMAKE_SYSTEM_NAME": "Linux",
            "CMAKE_SYSTEM_PROCESSOR": "aarch64",
        })
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["mimick"]
        self.cpp_info.set_property("cmake_file_name", "mimick")
        self.cpp_info.set_property("cmake_target_name", "mimick::mimick")
