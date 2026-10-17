#!/usr/bin/env python3
"""Conan recipe for grpc 1.84.0 (CMake) on HarmonyOS PC / aarch64.

gRPC is a large C++ RPC framework.  This recipe adapts **1.84.0** — re-derived
from the 1.70.0 recipe but re-verified line by line against the 1.84.0 source
tree (see notes.md for the full delta).

Dependencies come from the HarmonyOS registry (gRPC_*_PROVIDER=package):
  abseil-cpp/20260107.1, protobuf/33.6, c-ares/1.34.6, re2/2024-04-01,
  openssl/3.5.6, zlib/1.3.1

Key OHOS adaptation points for 1.84.0:
  - OHOS musl has no `pthread_cancel`; src/core/util/posix/thd.cc:204 would
    fail to link.  Patch 0001 stubs Thread::Kill behind GPR_NO_PTHREAD_CANCEL,
    which the toolchain defines.
  - CMakeDeps exports `c-ares::c-ares` / `openssl::openssl` while grpc expects
    `c-ares::cares` / `OpenSSL::SSL`; patches 0003 / 0004 accept the registry
    target names.
  - gpr_tmpfile() hard-codes /tmp; patch 0005 honours $TMPDIR instead, so the
    library works where /tmp is read-only.
  - abseil: the registry's abseil-cpp/20260107.1 installs the *upstream*
    abslConfig.cmake (ABSL_ENABLE_INSTALL=True) under lib/cmake/absl.  We
    point absl_DIR there so `find_package(absl REQUIRED CONFIG)` provides the
    real per-component targets (absl::check, absl::log_sink, ...).  The 1.70.0
    alias patch is NOT used: it was built for a 49-entry component list and
    1.84.0 references 59 components, 9 of which it did not define.
  - gRPC_BUILD_CSHARP_EXT was removed upstream in 1.84.0 and is no longer set.
  - Host tools: the proto code generators in CMakeLists.txt are reached only
    from code inside `if (gRPC_BUILD_TESTS)` (CMakeLists.txt:708) and from the
    `tools_c`/`tools_cxx`/`plugins` custom targets, none of which are in the
    default ALL build.  With gRPC_BUILD_TESTS=OFF the shipped library sources
    (pre-generated .pb.cc) compile without running protoc, so no host protoc
    is required for the library build.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class GrpcConan(ConanFile):
    name = "grpc"
    version = "1.84.0"
    description = "High performance, open source universal RPC framework"
    license = "Apache-2.0"
    homepage = "https://github.com/grpc/grpc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)
        # The vendored grpc-proto sources must travel with the recipe: Conan
        # runs build() with `recipe_folder` pointing at the *cache* copy
        # (p/<pkg>/e), so a file that is not exported simply is not there.
        # They are plain .proto text rather than an archive so the PR diff
        # stays text-only: a GitCode PR .diff cannot carry binary patch data,
        # and CI's checkout-pr step fails on it with
        # "missing binary patch data" before Conan ever runs.
        copy(self, "*",
             src=os.path.join(self.recipe_folder, "vendored-grpc-proto"),
             dst=os.path.join(self.export_sources_folder, "vendored-grpc-proto"))

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("grpc supports Linux and OHOS targets")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, "17")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("grpc supports OHOS armv8 only")

    def requirements(self):
        # absl ABI must be identical to protobuf/33.6's (lts_20260107).
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        self.requires("protobuf/33.6")
        self.requires("c-ares/1.34.6")
        self.requires("re2/2024-04-01")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        # grpc's source tree contains a file literally named `build` (a Bazel
        # BUILD file), which collides with cmake_layout's default `build/`
        # folder. Use a distinct build folder name.
        cmake_layout(self, build_folder="cmake-build")

    def environment(self):
        # lld (the OHOS SDK linker) needs libxml2.so.16 from the SDK's llvm/lib
        # at link time; without it the compiler link tests in cmake.configure
        # fail with "Error loading shared library libxml2.so.16".
        env = Environment()
        env.append_path(
            "LD_LIBRARY_PATH",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib")
        return env

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # grpc sets CMAKE_CXX_STANDARD only on Apple (CMakeLists.txt:289-293)
        # and otherwise relies on per-target cxx_std_17 features; pin it here
        # so the OHOS build cannot drift to an older default.
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        # Keep every heavy dep from the registry (never build from the empty
        # third_party/ submodule stubs).
        for provider in ("ABSL", "CARES", "PROTOBUF", "RE2", "SSL", "ZLIB"):
            tc.variables[f"gRPC_{provider}_PROVIDER"] = "package"
        tc.variables["gRPC_BUILD_CODEGEN"] = True
        tc.variables["gRPC_BUILD_TESTS"] = False
        tc.variables["gRPC_INSTALL"] = True
        tc.variables["gRPC_BUILD_GRPCPP_OTEL_PLUGIN"] = False
        # Only the C++ codegen plugin is needed; the other language plugins
        # add build time and their sources are not consumed here.
        for plugin in ("CSHARP", "NODE", "OBJECTIVE_C", "PHP", "PYTHON", "RUBY"):
            tc.variables[f"gRPC_BUILD_GRPC_{plugin}_PLUGIN"] = False
        # 1.84.0's six third_party archive dirs ship empty in the tarball and
        # the download guard is `NOT EXISTS <dir>` — but keep the network out
        # of configure entirely.
        tc.variables["gRPC_DOWNLOAD_ARCHIVES"] = False
        # New in 1.84.0: cmake/systemd.cmake is included for Linux/POSIX and
        # probes for systemd.  OHOS has no systemd; pin it off.
        tc.variables["gRPC_USE_SYSTEMD"] = False
        # OHOS lacks pthread_cancel, so Thread::Kill cannot cancel threads.
        # The platform decision lives in the build system (feature macro),
        # not in source, per the project rule against platform macros in
        # patches (see patches/0001-thd-pthread-cancel.patch).
        tc.preprocessor_definitions["GPR_NO_PTHREAD_CANCEL"] = True
        # NOTE: ABSL_PROPAGATE_CXX_STD is only read by grpc's
        # cmake/abseil-cpp.cmake under gRPC_ABSL_PROVIDER=module; with
        # "package" it is a no-op, so it is not set here.

        # grpc's ssl.cmake locates OpenSSL through the built-in FindOpenSSL
        # module, which needs the registry package root.
        tc.variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder.replace("\\", "/")

        # protobuf's registry package exports cmake_find_mode=none, so point
        # grpc's find_package(Protobuf CONFIG) at the installed config files
        # directly (mirrors protobuf's own test_package wiring).
        protobuf = self.dependencies["protobuf"]
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")

        # abseil-cpp installs the upstream abslConfig.cmake (it builds with
        # ABSL_ENABLE_INSTALL=True), which provides the real per-component
        # absl:: targets that grpc 1.84.0 links by name.  Point absl_DIR at it
        # instead of aliasing targets with a patch.
        abseil = self.dependencies["abseil-cpp"]
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._install_vendored_grpc_proto()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _install_vendored_grpc_proto(self):
        """Populate third_party/grpc-proto with the three .proto files the
        non-test codegen path needs.

        CMakeLists.txt:696-703 call
        protobuf_generate_grpc_cpp_with_import_path_correction() on
        third_party/grpc-proto/grpc/{channelz/v1,reflection/v1,reflection/v1alpha}/*.proto,
        and the function's first action is file(COPY ...) — which hard-fails if
        the file is missing (CMakeLists.txt:591).  That directory is a git
        submodule, so the release tarball ships it empty, and
        cmake/download_archive.cmake only downloads when the directory does
        NOT exist.  Ship the three upstream files with the recipe instead of
        depending on the network at configure time.

        They are stored as plain text, not as a .tar.gz: a GitCode PR .diff
        carries no binary payload, so a vendored archive makes CI's
        checkout-pr fail with "missing binary patch data".
        """
        # Exported via export_sources(), so prefer the exported copy and fall
        # back to the original recipe directory (direct `conan create <dir>`).
        src = os.path.join(self.export_sources_folder, "vendored-grpc-proto")
        if not os.path.isdir(src):
            src = os.path.join(self.recipe_folder, "vendored-grpc-proto")
        if not os.path.isdir(src):
            raise ConanException(
                f"vendored grpc-proto sources missing in both export_sources "
                f"and the recipe dir: {src}")
        dest = os.path.join(self.source_folder, "third_party", "grpc-proto")
        os.makedirs(dest, exist_ok=True)
        copy(self, "*", src=src, dst=dest)
        self.output.info(f"installed vendored grpc-proto into {dest}")

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Preserve grpc's component-rich CMake config (gRPC::grpc++ etc.)
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = ["grpc++", "grpc", "gpr"]
        self.cpp_info.bindirs = ["bin"]
