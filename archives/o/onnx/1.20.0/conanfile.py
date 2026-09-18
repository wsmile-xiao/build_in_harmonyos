#!/usr/bin/env python3
"""Conan recipe for ONNX 1.20.0 — CMake C++ library, OHOS aarch64.

W0 evidence (reports/DEPENDENCIES.md):
- protobuf/33.6.1 + abseil-cpp/20260107.1 + zlib/1.3.1 + googletest/1.17.0 are all published on ohpcd.
- protobuf registry package sets cmake_find_mode=none -> point Protobuf_DIR / utf8_range_DIR /
  absl_DIR at the installed config files directly (grpc/1.70.0 + etcd-cpp-apiv3 pattern).
- ONNX needs a *runnable* protoc: the target (aarch64) protoc cannot run on the x86_64 build
  host, so an explicit host protoc may be passed via ONNX_HOST_PROTOC (env) or the
  user.onnx:host_protoc conf. On native CI neither is set and the target protoc runs directly
  (no build-context protobuf, no extra dependency).
- ONNX only honours ONNX_CUSTOM_PROTOC_EXECUTABLE when protobuf::libprotobuf exists already;
  force it via CMAKE_PROJECT_INCLUDE so upstream CMakeLists stays unpatched.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save


class OnnxConan(ConanFile):
    name = "onnx"
    version = "1.20.0"
    description = "Open Neural Network Exchange (ONNX) C++ library"
    license = "Apache-2.0"
    homepage = "https://onnx.ai"
    url = "https://github.com/onnx/onnx"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "with_tests": [True, False]}
    default_options = {"shared": False, "fPIC": True, "with_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("protobuf/33.6.1", transitive_headers=True)
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        self.requires("zlib/1.3.1")
        if self.options.with_tests:
            # googletest (not gtest): its package exports cmake_file_name=GTest and
            # target GTest::gtest, which ONNX expects from find_package(GTest).
            # test_requires: only used to build the upstream gtests, not exposed to consumers.
            self.test_requires("googletest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]

        tc = CMakeToolchain(self)
        # protobuf registry package exports cmake_find_mode=none -> explicit config dirs
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf").replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range").replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl").replace("\\", "/")
        # ONNX build options
        tc.variables["ONNX_ML"] = True
        tc.variables["ONNX_BUILD_PYTHON"] = False
        tc.variables["ONNX_BUILD_TESTS"] = bool(self.options.with_tests)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        # Prefer Conan-generated *config* packages: ONNX calls find_package(GTest) without
        # CONFIG, which would otherwise take CMake's FindGTest module and link a bare -lgtest.
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        # Runnable protoc: the registry protoc targets aarch64 and cannot run on an x86_64 build
        # host. Priority: conf user.onnx:host_protoc > env ONNX_HOST_PROTOC (local cross) >
        # target protoc (native CI).
        host_protoc = os.path.join(
            protobuf.package_folder, "bin", "protoc").replace("\\", "/")
        conf_override = self.conf.get("user.onnx:host_protoc", default=None)
        env_override = os.environ.get("ONNX_HOST_PROTOC")
        if conf_override:
            host_protoc = str(conf_override).replace("\\", "/")
        elif env_override:
            self.output.warning(
                "using host protoc from ONNX_HOST_PROTOC (expected for local cross builds only)")
            host_protoc = env_override.replace("\\", "/")
        tc.variables["Protobuf_PROTOC_EXECUTABLE"] = host_protoc
        tc.variables["ONNX_CUSTOM_PROTOC_EXECUTABLE"] = host_protoc
        # Make protobuf::libprotobuf exist before ONNX evaluates its custom-protoc branch
        preload = os.path.join(self.generators_folder, "onnx_preload_protobuf.cmake")
        save(self, preload, "find_package(Protobuf CONFIG REQUIRED)\n")
        tc.variables["CMAKE_PROJECT_INCLUDE"] = preload.replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_tests and can_run(self):
            cmake.ctest(cli_args=["--output-on-failure", "--no-tests=error"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Consumers use the CMake config files installed by ONNX itself (namespace ONNX::):
        # the CMakeDeps wrapper cannot reproduce protobuf's find_mode=none target names.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = ["onnx", "onnx_proto"]
        self.cpp_info.requires = [
            "protobuf::protobuf",
            "abseil-cpp::abseil-cpp",
            "zlib::zlib",
        ]
