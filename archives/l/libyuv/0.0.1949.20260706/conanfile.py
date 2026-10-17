from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get
import os

class LibyuvConan(ConanFile):
    name = "libyuv"
    version = "0.0.1949.20260706"
    package_type = "library"
    license = "BSD-3-Clause"
    homepage = "https://chromium.googlesource.com/libyuv/libyuv/"
    url = "https://chromium.googlesource.com/libyuv/libyuv/"
    description = "YUV scaling and conversion library"
    topics = ("yuv", "video", "conversion", "scaling")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # Upstream UNIT_TEST uses GoogleTest only while compiling/running tests.
        # 1.17.0 is the version published in the ohpcd registry (1.14.0 is not
        # available there), and the recipe pins nothing else about gtest.
        self.tool_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.variables["LIBYUV_DISABLE_JPEG"] = True
        tc.variables["UNIT_TEST"] = True
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # The OHOS Conan toolchain does not populate this CMake variable;
        # libyuv uses it to add the AArch64 NEON/SVE translation units.
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # The OHOS clang target used by the runner does not expose the
        # intrinsics feature macros consistently.  Disable optional kernels
        # so generic dispatch does not reference unlinked NEON/SVE symbols.
        simd_flags = "-DLIBYUV_DISABLE_NEON -DLIBYUV_DISABLE_SVE -DLIBYUV_DISABLE_SVE2"
        tc.variables["CMAKE_C_FLAGS"] = simd_flags
        tc.variables["CMAKE_CXX_FLAGS"] = simd_flags
        gtest = self.dependencies.build["gtest"].package_folder
        tc.variables["GTEST_LIBRARY"] = os.path.join(gtest, "lib", "libgtest.a")
        tc.variables["CMAKE_CXX_FLAGS"] = simd_flags + " -I" + os.path.join(gtest, "include")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.run(os.path.join(self.build_folder, "libyuv_unittest"), cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "AUTHORS", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["yuv"]
        self.cpp_info.set_property("cmake_file_name", "libyuv")
        self.cpp_info.set_property("cmake_target_name", "libyuv::yuv")
        self.cpp_info.set_property("pkg_config_name", "libyuv")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
