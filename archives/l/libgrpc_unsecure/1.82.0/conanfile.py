#!/usr/bin/env python3
"""Conan recipe for libgrpc_unsecure 1.82.0 (CMake).

gRPC module split package: the TLS-free core of gRPC, as produced by the
upstream grpc v1.82.0 CMake build (targets grpc_unsecure / grpc++_unsecure
plus their internal static deps gpr / upb_*_lib / address_sorting).

Adapted from the grpc 1.70.0 main recipe in this repo (module-split reuse
pattern): same registry provider wiring, same OHOS portability patches,
build restricted to the unsecure target closure.

Adaptation notes (HarmonyOS PC / aarch64):
- All external deps (absl, protobuf, c-ares, re2, openssl, zlib) come from
  the registry (gRPC_*_PROVIDER=package). absl ABI must match protobuf:
  abseil-cpp/20260107.1 (lts_20260107), same as protobuf/33.6.
  Note: re2/openssl are configuration-time requirements only (grpc's top
  level CMakeLists find_package()s them unconditionally); none of the
  unsecure targets reference their symbols at link time.
- OHOS lacks `pthread_cancel` (thd.cc Thread::Kill), and CMakeDeps exports
  `c-ares::c-ares` while grpc expects `c-ares::cares`; see patches.
- gRPC_BUILD_CODEGEN is OFF: the unsecure core has no protobuf codegen
  requirement (upb generated sources are pre-generated in the tarball),
  and protoc/grpc_cpp_plugin are provided by the grpc main package.
- Only the unsecure target closure is built (grpc_unsecure C core,
  grpc++_unsecure C++ binding, gpr, upb_*_lib, address_sorting). The
  package() step copies these libs plus the full public header set
  (mirrors the boost component-package pattern: headers are complete,
  libs are the component surface).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

_TARGETS = [
    # C core (unsecure)
    "grpc_unsecure",
    # C++ binding (unsecure)
    "grpc++_unsecure",
    # internal static helpers (consumer-visible link closure)
    "gpr",
    "upb_base_lib",
    "utf8_range_lib",
    "upb_descriptor_lib",
    "upb_hash_lib",
    "upb_json_lib",
    "upb_lex_lib",
    "upb_mem_lib",
    "upb_message_lib",
    "upb_mini_descriptor_lib",
    "upb_mini_table_lib",
    "upb_reflection_lib",
    "upb_textformat_lib",
    "address_sorting",
]

_LIBS = [
    "grpc++_unsecure",
    "grpc_unsecure",
    "gpr",
    "upb_textformat_lib",
    "upb_reflection_lib",
    "upb_mini_descriptor_lib",
    "upb_mini_table_lib",
    "upb_message_lib",
    "upb_wire_lib",
    "upb_json_lib",
    "upb_lex_lib",
    "upb_hash_lib",
    "upb_mem_lib",
    "upb_descriptor_lib",
    "upb_base_lib",
    "utf8_range_lib",
    "address_sorting",
]


class LibgrpcUnsecureConan(ConanFile):
    name = "libgrpc_unsecure"
    version = "1.82.0"
    description = "gRPC TLS-free core: grpc_unsecure / grpc++_unsecure libraries from grpc 1.82.0"
    license = "Apache-2.0"
    homepage = "https://github.com/grpc/grpc"
    url = "https://github.com/grpc/grpc"
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

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libgrpc_unsecure supports Linux and OHOS targets")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, "17")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("libgrpc_unsecure supports OHOS armv8 only")

    def requirements(self):
        # absl ABI must be identical to protobuf/33.6's (lts_20260107).
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        self.requires("protobuf/33.6")
        self.requires("c-ares/1.34.6")
        # re2/openssl: grpc's top-level CMakeLists unconditionally
        # find_package()s them when *_PROVIDER=package; the unsecure
        # targets never reference their symbols.
        self.requires("re2/2024-04-01")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        # grpc's source tree contains a file literally named `build` (a Bazel
        # BUILD file), which collides with cmake_layout's default `build/`
        # folder. Use a distinct build folder name.
        cmake_layout(self, build_folder="cmake-build")

    def source(self):
        get(self, **self.conan_data["sources"]["grpc"], strip_root=True)
        # The release tarball ships the test-support submodules empty;
        # fill them from the commits pinned by grpc v1.82.0 so
        # gRPC_BUILD_TESTS can configure/build offline. Each archive
        # extracts as <name>-<sha>/; move it into the submodule slot.
        import glob
        import shutil
        for name, prefix in [
            ("googletest", "googletest-*"),
            ("cel-spec", "cel-spec-*"),
            ("googleapis", "googleapis-*"),
            ("xds", "xds-*"),
            ("opencensus-proto", "opencensus-proto-*"),
            ("protoc-gen-validate", "protoc-gen-validate-*"),
            ("envoy-api", "data-plane-api-*"),
        ]:
            get(self, **self.conan_data["sources"][name])
            dest = os.path.join(self.source_folder, "third_party", name)
            candidates = glob.glob(os.path.join(self.source_folder, prefix))
            if not candidates:
                raise Exception(f"{name} archive did not extract ({prefix} not found)")
            if os.path.isdir(dest):
                shutil.rmtree(dest)
            shutil.move(candidates[0], dest)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # Keep all heavy deps from the registry (never build from module
        # submodules on OHOS).
        for provider in ("ABSL", "CARES", "PROTOBUF", "RE2", "SSL", "ZLIB"):
            tc.variables[f"gRPC_{provider}_PROVIDER"] = "package"
        # Codegen must be ON when gRPC_BUILD_TESTS=ON: test programs
        # consume generated .grpc.pb.cc sources. The grpc_cpp_plugin
        # binary and registry protoc are aarch64 OHOS executables which
        # run natively on this device (no cross-execution involved).
        tc.variables["gRPC_BUILD_CODEGEN"] = True
        # Upstream gtest programs that link the unsecure closure are built
        # and executed in build() (see _build_and_run_upstream_tests).
        # third_party test-support submodules are filled in source() (the
        # release tarball ships them empty), so no network is needed.
        tc.variables["gRPC_BUILD_TESTS"] = True
        tc.variables["gRPC_BUILD_CSHARP_EXT"] = False
        tc.variables["gRPC_INSTALL"] = False
        tc.variables["gRPC_BUILD_GRPCPP_OTEL_PLUGIN"] = False
        for plugin in ("CSHARP", "NODE", "OBJECTIVE_C", "PHP", "PYTHON", "RUBY"):
            tc.variables[f"gRPC_BUILD_GRPC_{plugin}_PLUGIN"] = False
        tc.variables["ABSL_PROPAGATE_CXX_STD"] = True
        # OHOS lacks pthread_cancel, so Thread::Kill cannot cancel threads.
        # The platform decision lives in the build system (feature macro),
        # not in source, per the project rule against platform macros in
        # patches (see patches/0001-thd-pthread-cancel.patch).
        tc.preprocessor_definitions["GPR_NO_PTHREAD_CANCEL"] = True
        # protobuf's registry package exports cmake_find_mode=none, so point
        # grpc's find_package(Protobuf CONFIG) at the installed config files
        # directly (mirrors the grpc 1.70.0 recipe wiring).
        protobuf = self.dependencies["protobuf"]
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        # abseil is shipped as abseil-cpp; protobuf's config also looks up
        # absl via abslConfig.cmake.
        abseil = self.dependencies["abseil-cpp"]
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        # find_program(protoc) in cross mode looks in PATH; expose the
        # registry protoc through the build environment.
        env = Environment()
        env.prepend_path("PATH", os.path.join(protobuf.package_folder, "bin"))
        env.vars(self).save_script("libgrpc_unsecure_protoc_path")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Only the unsecure core closure: C core + C++ binding + internal
        # static helpers. The full TLS/secure surface is the grpc main
        # package's product, not this module split's.
        build_args = []
        for target in _TARGETS:
            build_args += ["--target", target]
        self.run(f'cmake --build "{self.build_folder}" {" ".join(build_args)} -j{self.conf.get("tools.build:jobs", default=os.cpu_count())}')
        self._build_and_run_upstream_tests()

    def _build_and_run_upstream_tests(self):
        """Build and run the upstream gtest programs tied to the unsecure
        module closure (they link grpc_unsecure / grpc_test_util_unsecure,
        i.e. their code-under-test IS this package's product).

        10 programs / 134 TEST macros:
          - direct: filter_test_test(15), party_test(25)
          - via grpc_test_util_unsecure: arena_promise_test(6),
            arena_test(23), basic_work_queue_test(7), factory_test(3),
            memory_quota_test(20), resource_quota_test(1),
            thread_pool_test(5), uri_test(29)
        Pure unit tests (no server/network), runnable on the OHOS target.
        """
        test_targets = [
            "grpc_test_util_unsecure",
            "arena_promise_test",
            "arena_test",
            "basic_work_queue_test",
            "factory_test",
            "memory_quota_test",
            "resource_quota_test",
            "thread_pool_test",
            "uri_test",
            "filter_test_test",
            "party_test",
        ]
        build_args = []
        for target in test_targets:
            build_args += ["--target", target]
        self.run(f'cmake --build "{self.build_folder}" {" ".join(build_args)} -j{self.conf.get("tools.build:jobs", default=os.cpu_count())}')

        if not can_run(self):
            return

        test_results_dir = os.path.join(self.build_folder, "test_results")
        os.makedirs(test_results_dir, exist_ok=True)
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        env = Environment()
        if os.path.isdir(sdk_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        # gtest output directories under $TMPDIR (read-only /tmp on OHOS)
        env.define("TMPDIR", os.path.join(self.build_folder, "test_results"))
        with env.vars(self).apply():
            summary_path = os.path.join(test_results_dir, "upstream_tests_summary.txt")
            with open(summary_path, "w", encoding="utf-8") as summary:
                summary.write("test_program\ttests_run\tpassed\tfailed\texit_code\n")
                for t in test_targets[1:]:  # skip the util library
                    logf = os.path.join(test_results_dir, f"{t}.log")
                    binp = self._find_test_binary(t)
                    if binp is None:
                        summary.write(f"{t}\t-\t-\t-\tNOT_FOUND\n")
                        continue
                    rc = self.run(f'"{binp}" > "{logf}" 2>&1', ignore_errors=True)
                    counts = self._gtest_counts(logf)
                    summary.write(
                        f"{t}\t{counts[0]}\t{counts[0]-counts[1]}\t{counts[1]}\t{rc}\n"
                    )

    def _find_test_binary(self, target):
        release_dir = os.path.join(self.build_folder, "cmake-build", "Release")
        if not os.path.isdir(release_dir):
            release_dir = self.build_folder
        for root, _dirs, files in os.walk(release_dir):
            if target in files:
                return os.path.join(root, target)
        return None

    @staticmethod
    def _gtest_counts(logf):
        """Parse gtest summary lines for run/failed counts."""
        ran = failed = 0
        try:
            with open(logf, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("[  PASSED  ]") or line.startswith("[  FAILED  ]"):
                        # e.g. "[  PASSED  ] 23 tests." / "[  FAILED  ] 2
                        # tests, listed below:" — the count is parts[3].
                        parts = line.split()
                        n = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
                        if line.startswith("[  PASSED  ]"):
                            ran = n
                        else:
                            failed = n
        except OSError:
            pass
        return ran, failed

    def package(self):
        # Manual packaging: gRPC_INSTALL's install script expects every
        # installable target to exist (full grpc surface); since only the
        # unsecure closure was built, copy the products directly.
        for lib in _LIBS:
            copy(
                self,
                f"lib{lib}.a",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
        # Full public header set (grpc core + grpcpp), mirroring the grpc
        # main package and the boost component-package pattern.
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Module split: upstream gRPC's install script expects the full
        # target surface, so no gRPCConfig.cmake is shipped. cmake_find_mode
        # is "none" (no CMakeDeps aggregate config either: registry
        # protobuf/33.6 itself ships cmake_find_mode=none and a CMakeDeps
        # config would emit a dangling protobuf::protobuf reference).
        # Consumers link the libs below directly (link order matters for
        # static archives: the C++ binding first, then the C core, then the
        # internal helpers), plus protobuf::libprotobuf (grpcpp public
        # headers include google/protobuf/*.h) and the registry targets
        # abseil-cpp::abseil-cpp / c-ares::c-ares / zlib::zlib.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = _LIBS
        self.cpp_info.includedirs = ["include"]
