from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.scm import Version
import os


class ZlogConan(ConanFile):
    name = "zlog"
    version = "1.2.18"
    description = "A reliable, high-performance, thread safe, flexible, clear-model, pure C logging library"
    license = "Apache-2.0"
    url = "https://github.com/HardySimpson/zlog"
    homepage = "https://github.com/HardySimpson/zlog"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Fetch the official upstream archive and verify its SHA-256
        # (conandata.yml sources.<version>), closing the loop on the
        # official source checksum. No vendored source tree is committed.
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["UNIT_TEST"] = "OFF"
        # Force consistent naming so we can find outputs
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
            "ON" if self.options.get_safe("fPIC", True) else "OFF"
        )
        # Upstream zlog 1.2.18 sets cmake_minimum_required(VERSION 2.8.5),
        # which is removed in CMake >= 3.27. Force the new policy floor so
        # modern CMake (OHOS toolchain ships CMake 3.x) accepts it.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os == "OHOS":
            tc.variables["ZLOG_OHOS_BUILD"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE",
             dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["zlog"]
        self.cpp_info.system_libs = ["pthread"]
        if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs.append("m")