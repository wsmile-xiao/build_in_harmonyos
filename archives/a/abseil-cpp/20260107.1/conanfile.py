from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, collect_libs, export_conandata_patches, get


class AbseilCppConan(ConanFile):
    name = "abseil-cpp"
    version = "20260107.1"
    description = "Google C++ common libraries"
    license = "Apache-2.0"
    homepage = "https://abseil.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["ABSL_ENABLE_INSTALL"] = True
        toolchain.variables["ABSL_PROPAGATE_CXX_STD"] = True
        toolchain.variables["BUILD_TESTING"] = False
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        toolchain.variables["CMAKE_CXX_STANDARD"] = 17
        toolchain.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = sorted(collect_libs(self))
        self.cpp_info.set_property("cmake_file_name", "abseil-cpp")
        self.cpp_info.set_property("cmake_target_name", "abseil-cpp::abseil-cpp")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
