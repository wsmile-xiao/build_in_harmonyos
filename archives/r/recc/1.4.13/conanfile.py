#!/usr/bin/env python3
"""Conan recipe for recc 1.4.13 (BuildGrid/buildbox monorepo).

recc is the "remote execution caching compiler" from the BuildGrid/buildbox
1.4.13 monorepo. The recipe builds only the `recc` tool (plus the
`common`/`commonmetrics`/`protos` libraries it depends on inside the same
source tree), links against registry gRPC/Protobuf/absl/OpenSSL/zlib/uuid/
tomlplusplus, and runs the upstream gtest suite.

Adaptation notes (HarmonyOS PC / aarch64):
- grpc/1.70.0 (registry-adapted) provides gRPC::grpc++ and grpc_cpp_plugin.
- buildbox-common's `pkg_check_modules(uuid REQUIRED)` needs uuid.pc; the
  registry uuid/2.40.1 package ships it, exposed via PkgConfigDeps.
- OCI support (CURL + nlohmann_json) is disabled: recc does not need it.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class ReccConan(ConanFile):
    name = "recc"
    version = "1.4.13"
    description = "Remote execution caching compiler (BuildGrid/buildbox)"
    license = "Apache-2.0"
    homepage = "https://gitlab.com/BuildGrid/buildbox/buildbox"
    url = "https://gitlab.com/BuildGrid/buildbox/buildbox"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
    }
    default_options = {
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("recc supports Linux and OHOS targets")

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("recc supports OHOS armv8 only")

    def requirements(self):
        self.requires("grpc/1.70.0")
        self.requires("protobuf/33.6")
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        self.requires("c-ares/1.34.6")
        self.requires("re2/2024-04-01")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")
        # buildbox-common links libuuid via pkg-config (uuid.pc).
        self.requires("uuid/2.40.1")
        self.requires("tomlplusplus/3.4.0")
        # Upstream gtest suite: buildbox's BuildboxGTestSetup.cmake does
        # find_package(GTest CONFIG) and links GTest::gtest/gmock.
        self.requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self, build_folder="cmake-build")

    def source(self):
        get(self, **self.conan_data["sources"]["buildbox"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        # Expose uuid.pc (and others) to pkg_check_modules in buildbox-common.
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        # Build only the recc tool; disable every other monorepo tool.
        tc.variables["TOOLS"] = "OFF"
        tc.variables["RECC"] = "ON"
        # deps.cmake only pulls ZLIB (and the static grpc linker rule) when
        # BUILD_STATIC is set; without it the recc link misses inflate/deflate.
        tc.variables["BUILD_STATIC"] = True
        for tool in (
            "CASD", "CASD_WRAP", "CASDOWNLOAD", "CASUPLOAD", "CASUPLOAD_OCI",
            "FUSE", "LOGSTREAMRECEIVER", "LOGSTREAMTAIL", "OUTPUTSTREAMER",
            "REXPLORER", "RUMBAD", "RUN_BUBBLEWRAP", "RUN_HOSTTOOLS",
            "RUN_OCI", "RUN_USERCHROOT", "TREXE", "WORKER",
        ):
            tc.variables[tool] = "OFF"
        # OCI support needs CURL + nlohmann_json; not needed by recc.
        tc.variables["OCI"] = "OFF"
        # Keep the upstream gtest suite buildable.
        tc.variables["BUILD_TESTING"] = True
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        # buildbox enables target_precompile_headers; on OHOS clang the PCH
        # build vs. per-target PIE flags mismatch ("is pie differs in PCH
        # file vs. current file"), so disable PCH entirely.
        tc.variables["CMAKE_DISABLE_PRECOMPILE_HEADERS"] = True
        # Point find_package() at the registry config files (protobuf's
        # package ships cmake_find_mode=none).
        protobuf = self.dependencies["protobuf"]
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        grpc_pkg = self.dependencies["grpc"]
        tc.variables["gRPC_DIR"] = os.path.join(
            grpc_pkg.package_folder, "lib", "cmake", "grpc"
        ).replace("\\", "/")
        # buildbox's protoc_compile() calls find_program(PROTOC protoc) and
        # find_program(GRPC_CPP_PLUGIN grpc_cpp_plugin); expose the registry
        # tools through CMAKE_PROGRAM_PATH.
        tc.variables["CMAKE_PROGRAM_PATH"] = ";".join(
            os.path.join(pkg.package_folder, "bin").replace("\\", "/")
            for pkg in (protobuf, grpc_pkg)
        )
        abseil = self.dependencies["abseil-cpp"]
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        toml = self.dependencies["tomlplusplus"]
        tc.variables["tomlplusplus_DIR"] = os.path.join(
            toml.package_folder, "lib", "cmake", "tomlplusplus"
        ).replace("\\", "/")
        tc.variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder.replace("\\", "/")
        tc.variables["ZLIB_ROOT"] = self.dependencies["zlib"].package_folder.replace("\\", "/")
        # buildbox's BuildboxGTestSetup.cmake does find_package(GTest CONFIG)
        # and links GTest::gtest/gtest_main/gmock. The registry gtest package
        # installs its native GTestConfig.cmake (with those targets) under
        # lib/cmake/GTest — point GTest_DIR there so the native config wins
        # over CMakeDeps' single-target gtest-config.cmake.
        gtest_pkg = self.dependencies["gtest"]
        tc.variables["GTest_DIR"] = os.path.join(
            gtest_pkg.package_folder, "lib", "cmake", "GTest"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
