from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class FdkAacConan(ConanFile):
    name = "fdk-aac"
    version = "2.0.3.2"
    description = "A standalone Fraunhofer FDK AAC codec library"
    license = "FDK-AAC"
    homepage = "https://sourceforge.net/projects/opencore-amr/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 构建上游自检程序 aac-enc(install)与 test-encode-decode(留在构建树,
        # 不 install——test_package 把上游源 vendor 进包内重新编译)。
        tc.variables["BUILD_PROGRAMS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 真机 OHOS 沙箱进程配额有限:ninja 默认并行度(cores+2,20 核实测 ≈45
        # 活进程)触发 posix_spawn EAGAIN 中道崩殂,必须限并发。
        cmake.build(cli_args=["--parallel", "8"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "NOTICE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["fdk-aac"]
