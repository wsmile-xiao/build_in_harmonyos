from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibaegisConan(ConanFile):
    name = "libaegis"
    version = "0.10.6"
    description = "High-performance AEGIS-128L, AEGIS-128X2, AEGIS-128X4, AEGIS-256, AEGIS-256X2 and AEGIS-256X4 AEAD algorithms"
    license = "MIT"
    homepage = "https://github.com/aegis-aead/libaegis"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "favor_performance": [True, False]}
    default_options = {"shared": False, "favor_performance": False}

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: system-name libraries default to static unless shared=True
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Side-channel mitigations by default; FAVOR_PERFORMANCE trades them away.
        tc.variables["FAVOR_PERFORMANCE"] = "ON" if self.options.favor_performance else "OFF"
        # WASM-only option; harmless but pin it off for native targets.
        tc.variables["AEGIS_WASM_RELAXED_SIMD"] = "OFF"
        if self.settings.os == "OHOS" and self.options.shared:
            # No Platform/HarmonyOS.cmake module in CMake: the Linux module
            # that defines CMAKE_SHARED_LIBRARY_SONAME_C_FLAG is not loaded,
            # so the upstream set_target_properties(SOVERSION 0) never turns
            # into a -Wl,-soname flag and libaegis.so ships without DT_SONAME
            # (see knowledge/DRAFT-libharu-2.3.0-missing-dt-soname.md).
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["aegis"]
        self.cpp_info.set_property("cmake_file_name", "aegis")
        self.cpp_info.set_property("cmake_target_name", "aegis::aegis")
