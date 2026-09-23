#!/usr/bin/env python3
"""Conan recipe for ONNX 1.22.0 (CMake, OHOS).

ONNX is the Open Neural Network Exchange: an open format to represent machine
learning models. The C++ core is a protobuf-backed IR library plus checker /
shape-inference / parser components.

Build notes for HarmonyOS PC (aarch64):
- Host and target are both OHOS aarch64 here, so the packaged protoc from the
  protobuf Conan package can be executed directly; no separate host-protoc
  build step is needed (unlike Windows-hosted cross builds).
- ONNX detects Protobuf via CONFIG mode: we point Protobuf_DIR / absl_DIR /
  utf8_range_DIR at the package-installed CMake configs so that
  `TARGET protobuf::libprotobuf` exists and the FetchContent fallback is
  avoided.
- Python bindings are intentionally not built (ONNX_BUILD_PYTHON=OFF); the
  deliverable is the C++ library and the onnx.proto toolchain outputs.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class OnnxConan(ConanFile):
    name = "onnx"
    version = "1.22.0"
    description = "Open Neural Network Exchange: open format to represent machine learning models"
    license = "Apache-2.0"
    homepage = "https://github.com/onnx/onnx"
    url = "https://github.com/onnx/onnx"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("onnx supports Linux and OHOS targets")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, "17")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("onnx supports OHOS armv8 only")

    def requirements(self):
        self.requires("protobuf/33.6.1", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["onnx"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]

        tc = CMakeToolchain(self)
        # protobuf ships its own CMake config (cmake_find_mode=none); point
        # ONNX at the package-installed configs so the CONFIG-mode probe
        # succeeds and protobuf::libprotobuf is available at configure time.
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        _protoc = os.path.join(protobuf.package_folder, "bin", "protoc").replace("\\", "/")
        tc.variables["ONNX_CUSTOM_PROTOC_EXECUTABLE"] = _protoc
        # ONNX's legacy probe path calls ``find_program(protoc)``; pre-seeding the
        # CMake cache variable lets it resolve to the packaged protoc directly.
        # NOTE: do not inject this via PATH / ``save_script("conanbuild")`` - a
        # recipe-written ``conanbuild.sh`` collides with Conan's own aggregate
        # ``conanbuild.sh`` and makes it source itself, recursing until the build
        # shell segfaults (ConanException "Error -11 while executing").
        tc.variables["Protobuf_PROTOC_EXECUTABLE"] = _protoc
        tc.variables["ONNX_BUILD_PYTHON"] = False
        tc.variables["ONNX_BUILD_TESTS"] = bool(self.options.build_tests)
        tc.variables["ONNX_ML"] = True
        tc.variables["ONNX_INSTALL"] = True
        tc.variables["ONNX_USE_PROTOBUF_SHARED_LIBS"] = False
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
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
        self.cpp_info.libs = ["onnx"]
        self.cpp_info.set_property("cmake_file_name", "onnx")
        self.cpp_info.set_property("cmake_target_name", "onnx::onnx")
        self.cpp_info.set_property("pkg_config_name", "onnx")
        # libonnx embeds generated .pb.cc objects; downstream consumers must
        # also link protobuf. The protobuf package keeps its own CMake config,
        # so consumers should find_package(Protobuf CONFIG) themselves.
        self.cpp_info.requires = ["protobuf::protobuf"]
