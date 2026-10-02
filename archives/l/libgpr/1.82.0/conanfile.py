#!/usr/bin/env python3
"""Conan recipe for libgpr 1.82.0 (CMake).

gRPC module split package: the `gpr` target of the upstream grpc v1.82.0
CMake build (Google Portable Runtime: logging, time, sync, alloc, env, cpu,
mpscq, host/port strings) packaged on its own so that the other gRPC
component packages (libgrpc_unsecure, libgrpc_authorization_provider, ...)
can depend on it instead of rebuilding the runtime.

Adapted from libgrpc_unsecure/1.82.0 in this repo (module-split reuse
pattern): same registry provider wiring, same OHOS portability patches,
build restricted to the `gpr` target.

Adaptation notes (HarmonyOS PC / aarch64):
- gpr links only abseil at build time (22 absl components); protobuf /
  c-ares / re2 / openssl / zlib are configuration-time requirements because
  grpc's top level CMakeLists find_package()s them unconditionally when
  gRPC_*_PROVIDER=package.
- OHOS lacks pthread_cancel (src/core/util/posix/thd.cc Thread::Kill) ->
  GPR_NO_PTHREAD_CANCEL (build-system feature macro, no platform macro in
  source, see patches/0001).
- CMakeDeps exports abseil-cpp::abseil-cpp / c-ares::c-ares / openssl::openssl
  / zlib::zlib while grpc expects absl::* / c-ares::cares / OpenSSL::SSL /
  ZLIB::ZLIB -> patches 0002-0004/0006 bridge the names.
- Upstream tests: the tests under test/core/util/ that exercise gpr
  (time_test, host_port_test, mpscq_test, string_test, sync_test, ...) link
  `grpc_test_util`, a test-only helper that pulls the full grpc core; that
  helper is the libgrpc_unsecure package's product, not gpr's.  This
  package therefore builds and runs the gpr-linked unit tests whose link
  closure is gpr + absl + gtest only (see _TEST_TARGETS).
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

_TARGET = "gpr"
_LIBS = ["gpr"]


def _sdk_lib_dir(conanfile):
    """Directory holding libc++_shared.so / libunwind.so for OHOS."""
    candidates = [
        "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native"
        "/llvm/lib/aarch64-linux-ohos",
    ]
    try:
        import json
        execs = conanfile.conf.get("tools.build:compiler_executables")
        if isinstance(execs, str):
            execs = json.loads(execs)
        cc = (execs or {}).get("c") or (execs or {}).get("cpp") or ""
        if cc:
            llvm = os.path.dirname(os.path.dirname(cc))
            candidates.append(os.path.join(llvm, "lib", "aarch64-linux-ohos"))
    except Exception:
        pass
    for cand in candidates:
        if os.path.isdir(cand):
            return cand
    return ""

# Unit tests whose upstream link closure is gpr + absl + gtest only.
_TEST_TARGETS = [
    "avl_test",
    "common_closures_test",
    "down_cast_test",
    "endpoint_config_test",
    "experiments_tag_test",
    "experiments_test",
    "memory_usage_test",
    "notification_test",
    "single_set_ptr_test",
    "slice_string_helpers_test",
    "status_flag_test",
    "stream_quota_test",
    "test_core_util_time_test",
    "timer_list_test",
    "useful_test",
]


class LibgprConan(ConanFile):
    name = "libgpr"
    version = "1.82.0"
    description = "gRPC Portable Runtime (gpr) library from grpc 1.82.0"
    license = "Apache-2.0"
    homepage = "https://github.com/grpc/grpc"
    url = "https://github.com/grpc/grpc"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libgpr supports Linux and OHOS targets")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, "17")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("libgpr supports OHOS armv8 only")

    def requirements(self):
        # absl ABI must match protobuf/33.6 (lts_20260107).
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        # Configuration-time only: grpc's top-level CMakeLists
        # find_package()s them when *_PROVIDER=package; no gpr symbol is
        # taken from them.
        self.requires("protobuf/33.6")
        self.requires("c-ares/1.34.6")
        self.requires("re2/2024-04-01")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        # grpc's source tree contains a file literally named `build` (a Bazel
        # BUILD file), which collides with cmake_layout's default `build/`.
        cmake_layout(self, build_folder="cmake-build")

    def source(self):
        get(self, **self.conan_data["sources"]["grpc"], strip_root=True)
        # The release tarball ships the test-support submodules empty; fill
        # them from the commits pinned by grpc v1.82.0 so gRPC_BUILD_TESTS
        # can configure/build offline. Each archive extracts as
        # <name>-<sha>/; move it into the submodule slot.
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
        for provider in ("ABSL", "CARES", "PROTOBUF", "RE2", "SSL", "ZLIB"):
            tc.variables[f"gRPC_{provider}_PROVIDER"] = "package"
        # Codegen must be ON when gRPC_BUILD_TESTS=ON (test programs consume
        # generated .grpc.pb.cc sources); the grpc_cpp_plugin target then
        # exists at configure time but is never built here (only gpr and the
        # selected test targets are).
        tc.variables["gRPC_BUILD_CODEGEN"] = True
        tc.variables["gRPC_BUILD_TESTS"] = True
        tc.variables["gRPC_BUILD_CSHARP_EXT"] = False
        tc.variables["gRPC_INSTALL"] = False
        tc.variables["gRPC_BUILD_GRPCPP_OTEL_PLUGIN"] = False
        for plugin in ("CSHARP", "NODE", "OBJECTIVE_C", "PHP", "PYTHON", "RUBY"):
            tc.variables[f"gRPC_BUILD_GRPC_{plugin}_PLUGIN"] = False
        tc.variables["ABSL_PROPAGATE_CXX_STD"] = True
        tc.preprocessor_definitions["GPR_NO_PTHREAD_CANCEL"] = True
        protobuf = self.dependencies["protobuf"]
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf").replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range").replace("\\", "/")
        abseil = self.dependencies["abseil-cpp"]
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl").replace("\\", "/")
        env = Environment()
        env.prepend_path("PATH", os.path.join(protobuf.package_folder, "bin"))
        env.vars(self).save_script("libgpr_protoc_path")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        jobs = self.conf.get("tools.build:jobs", default=os.cpu_count())
        self.run(f'cmake --build "{self.build_folder}" --target {_TARGET} -j{jobs}')
        self.run(
            f'cmake --build "{self.build_folder}" '
            + " ".join(f"--target {t}" for t in _TEST_TARGETS)
            + f" -j{jobs}")
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        if not can_run(self):
            return
        results = os.path.join(self.build_folder, "test_results")
        os.makedirs(results, exist_ok=True)
        env = Environment()
        sdk_lib = _sdk_lib_dir(self)
        if sdk_lib:
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        env.define("TMPDIR", results)
        with env.vars(self).apply():
            summary_path = os.path.join(results, "upstream_tests_summary.txt")
            with open(summary_path, "w", encoding="utf-8") as summary:
                summary.write("test_program\ttests_run\tpassed\tfailed\texit_code\n")
                for target in _TEST_TARGETS:
                    binary = self._find_test_binary(target)
                    if binary is None:
                        summary.write(f"{target}\t-\t-\t-\tNOT_FOUND\n")
                        continue
                    logf = os.path.join(results, f"{target}.log")
                    rc = self.run(f'"{binary}" > "{logf}" 2>&1', ignore_errors=True)
                    ran, failed = self._gtest_counts(logf)
                    summary.write(f"{target}\t{ran}\t{ran - failed}\t{failed}\t{rc}\n")
            self.output.info(open(summary_path, encoding="utf-8").read())

    def _find_test_binary(self, target):
        release = os.path.join(self.build_folder, "cmake-build", "Release")
        if not os.path.isdir(release):
            release = self.build_folder
        names = {target}
        # grpc CMake sometimes registers test_core_util_foo_test while the
        # executable is emitted as foo_test.
        parts = target.split("_")
        for i in range(1, len(parts)):
            names.add("_".join(parts[i:]))
        for root, _dirs, files in os.walk(release):
            for name in files:
                if name in names:
                    return os.path.join(root, name)
        return None

    @staticmethod
    def _gtest_counts(logf):
        ran = failed = 0
        try:
            with open(logf, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("[  PASSED  ]") or line.startswith("[  FAILED  ]"):
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
        copy(self, "libgpr.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Module split: no CMake config (upstream install expects the full
        # target surface). Consumers link libgpr.a directly plus
        # abseil-cpp::abseil-cpp.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = _LIBS
        self.cpp_info.includedirs = ["include"]