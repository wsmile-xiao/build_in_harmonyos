import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class WasmEdgeConan(ConanFile):
    name = "wasmedge"
    version = "0.17.1"
    description = "WasmEdge is a lightweight, high-performance WebAssembly runtime"
    license = "Apache-2.0"
    homepage = "https://github.com/WasmEdge/WasmEdge"
    url = "https://github.com/WasmEdge/WasmEdge"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WASMEDGE_BUILD_TESTS"] = "OFF"
        tc.variables["WASMEDGE_BUILD_COVERAGE"] = "OFF"
        tc.variables["WASMEDGE_BUILD_SHARED_LIB"] = "ON" if self.options.shared else "OFF"
        tc.variables["WASMEDGE_BUILD_STATIC_LIB"] = "OFF" if self.options.shared else "ON"
        tc.variables["WASMEDGE_BUILD_TOOLS"] = "OFF"
        tc.variables["WASMEDGE_BUILD_PLUGINS"] = "OFF"
        tc.variables["WASMEDGE_BUILD_EXAMPLE"] = "OFF"
        tc.variables["WASMEDGE_BUILD_WASI_NN_RPC"] = "OFF"
        tc.variables["WASMEDGE_USE_LLVM"] = "OFF"
        tc.variables["WASMEDGE_FORCE_DISABLE_LTO"] = "ON"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.variables["CMAKE_CXX_FLAGS"] = "-Wno-error=maybe-uninitialized -Wno-error=array-bounds"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["wasmedge"]
        self.cpp_info.bindirs = []
