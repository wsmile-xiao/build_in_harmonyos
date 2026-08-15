from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibdiscidConan(ConanFile):
    name = "libdiscid"
    version = "0.6.5"
    description = "MusicBrainz DiscID library for audio CD identification"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/metabrainz/libdiscid"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os == "OHOS":
            self.options.shared = False
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = (
            False if self.settings.os == "OHOS" else bool(self.options.shared)
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run upstream tests (ADD_CUSTOM_TARGET check): test_core/test_put/test_read/test_read_full
        cmake.build(target="check")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["discid"]
# OHOS-CI-trigger: re-run build (no functional change)
