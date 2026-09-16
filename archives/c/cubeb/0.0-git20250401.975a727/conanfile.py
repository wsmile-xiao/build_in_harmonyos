from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CubebConan(ConanFile):
    name = "cubeb"
    version = "0.0-git20250401.975a727"
    description = "Cross platform audio library by Mozilla"
    license = "ISC"
    homepage = "https://github.com/mozilla/cubeb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "build_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "build_tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.build_tests:
            self.requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Static library (BUILD_SHARED_LIBS=OFF)
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        # No Rust backends
        tc.cache_variables["BUILD_RUST_LIBS"] = "OFF"
        # Lazy load audio backend libs (skip hard deps on pulse/alsa/jack)
        tc.cache_variables["LAZY_LOAD_LIBS"] = "ON"
        # Tests: controlled by conan option
        tc.cache_variables["BUILD_TESTS"] = "ON" if self.options.build_tests else "OFF"
        # Disable sanitizers (not needed for production build)
        tc.cache_variables["USE_SANITIZERS"] = "OFF"
        # Build tools
        tc.cache_variables["BUILD_TOOLS"] = "OFF"
        # Bundle speex (internal subprojects/speex)
        tc.cache_variables["BUNDLE_SPEEX"] = "OFF"
        # Disable Android backends: OHOS has android/log.h but lacks full
        # SLES/JNI/AAudio NDK headers. check_include_files would detect
        # android/log.h and SLES/OpenSLES.h, enabling cubeb_opensl.cpp and
        # cubeb-jni.cpp which require the full Android NDK.
        tc.cache_variables["USE_OPENSL"] = "OFF"
        tc.cache_variables["USE_AUDIOTRACK"] = "OFF"
        tc.cache_variables["USE_AAUDIO"] = "OFF"
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
        self.cpp_info.libs = ["cubeb"]
        # cubeb needs dl and pthread on Linux/OHOS
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
