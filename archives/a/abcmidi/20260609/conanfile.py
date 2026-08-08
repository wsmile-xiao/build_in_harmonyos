from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class AbcMidiConan(ConanFile):
    name = "abcmidi"
    version = "20260609"
    description = "Command-line tools for ABC music notation and MIDI conversion"
    license = "GPL-2.0-or-later"
    homepage = "https://ifdo.ca/~seymour/runabc/top.html"
    url = "https://github.com/sshlien/abcmidi"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload URLs end in the tag name (e.g. ".../tar.gz/refs/tags/2026.06.06")
        # which has no file extension, so Conan's get() deduces filename "2026.06.06"
        # and unzip() falls back to the zip decoder → BadZipFile.  Pass an explicit
        # *.tar.gz filename so unzip() selects the tar.gz decoder.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="abcmidi-2026.06.06.tar.gz")

    def generate(self):
        toolchain = CMakeToolchain(self)
        # CMake has no OHOS platform module.  The package is built natively
        # on OHOS with clang and does not rely on Linux-specific APIs.
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
