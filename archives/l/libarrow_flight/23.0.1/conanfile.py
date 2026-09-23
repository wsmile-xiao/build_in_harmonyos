import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir

required_conan_version = ">=2.1.0"


class LibarrowFlightConan(ConanFile):
    name = "libarrow_flight"
    version = "23.0.1"
    description = "Apache Arrow Flight RPC - gRPC-based data transport for Arrow (Arrow Flight SQL extension included)"
    license = ("Apache-2.0",)
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    homepage = "https://arrow.apache.org/"
    topics = ("arrow", "flight", "grpc", "rpc", "data-transport", "aarch64")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "compute": [True, False],
        "csv": [True, False],
        "filesystem_layer": [True, False],
        "ipc": [True, False],
        "json": [True, False],
        "with_boost": [True, False],
        "with_bz2": [True, False],
        "with_lz4": [True, False],
        "with_snappy": [True, False],
        "with_zlib": [True, False],
        "with_zstd": [True, False],
        "with_re2": [True, False],
        "with_utf8proc": [True, False],
        "with_openssl": [True, False],
        "flight_sql": [True, False],
        "simd_level": [None, "default", "sse4_2", "avx2", "avx512", "neon"],
        "runtime_simd_level": [None, "sse4_2", "avx2", "avx512", "max"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "compute": True,
        "csv": True,
        "filesystem_layer": True,
        "ipc": True,
        "json": True,
        "with_boost": True,
        "with_bz2": True,
        "with_lz4": True,
        "with_snappy": True,
        "with_zlib": True,
        "with_zstd": True,
        "with_re2": True,
        "with_utf8proc": True,
        "with_openssl": True,
        "flight_sql": True,
        "simd_level": "default",
        "runtime_simd_level": "max",
    }

    short_paths = True

    # Ship the gRPC target bridge module (cmake/bridge-grpc-targets.cmake)
    # with the recipe — package() copies it into the package and
    # cmake_build_modules makes CMakeDeps include it downstream.
    exports_sources = "cmake/*"

    @property
    def _min_cppstd(self):
        # Arrow 23.0.1 requires C++20 (SetupCxxFlags.cmake enforces >= 20)
        return "20"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Arrow 23.0.1 requires C++20 (SetupCxxFlags.cmake enforces >= 20)
        self.settings.compiler.cppstd = 20
        # Enable fPIC for all dependencies (needed when ARROW_BUILD_TESTS=ON
        # creates shared module libraries like arrow_filesystem_example)
        self.options["zlib/*"].fPIC = True
        self.options["bzip2/*"].fPIC = True
        self.options["lz4/*"].fPIC = True
        self.options["zstd/*"].fPIC = True
        self.options["boost/*"].fPIC = True
        self.options["re2/*"].fPIC = True
        # gRPC 1.70.0 from the registry is built against openssl/3.5.6 —
        # keep the whole dependency graph on a single openssl to avoid
        # duplicate symbol / ABI mismatch at link time.
        self.options["openssl/*"].shared = False
        self.options["grpc/*"].shared = False
        self.options["protobuf/*"].shared = False
        self.options["protobuf/*"].with_zlib = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def build_requirements(self):
        if self.settings.os in ("Linux", "OHOS"):
            # GTest needed for ARROW_BUILD_TESTS=ON (upstream test execution)
            self.test_requires("gtest/1.17.0.1")
            self.test_requires("gflags/2.2.2.1")

    def requirements(self):
        # ⭐ Flight is a gRPC module — grpc/1.70.0 brings its own pinned
        # dependency set (protobuf/33.6 + abseil-cpp/20260107.1 +
        # c-ares/1.34.6 + openssl/3.5.6 + re2 + zlib). Everything here must
        # stay ABI-compatible with grpc's registry build.
        self.requires("grpc/1.70.0")
        # protobuf is a direct requirement too: consumers of arrow_flight
        # link generated protobuf code against protobuf::libprotobuf, and
        # grpc itself only exposes it transitively (cmake_find_mode=none).
        self.requires("protobuf/33.6")
        # sqlite3 is needed by the Flight SQL test server (upstream tests)
        if self.options.flight_sql:
            self.requires("sqlite3/3.49.1")
        if self.options.with_boost:
            self.requires("boost/1.84.0")
        if self.options.with_bz2:
            self.requires("bzip2/1.0.8")
        if self.options.with_lz4:
            self.requires("lz4/1.10.0")
        if self.options.with_snappy:
            self.requires("snappy/1.1.7")
        if self.options.with_zlib:
            self.requires("zlib/1.3.1")
        if self.options.with_zstd:
            self.requires("zstd/1.5.7")
        if self.options.with_re2:
            self.requires("re2/2024-04-01")
        if self.options.with_utf8proc:
            self.requires("utf8proc/2.11.3")
        if self.options.with_openssl:
            # Must match grpc/1.70.0's pinned openssl (3.5.6)
            self.requires("openssl/3.5.6")
        if self.options.json:
            self.requires("rapidjson/1.1.0")
        if self.options.get_safe("simd_level") is not None or \
                self.options.get_safe("runtime_simd_level") is not None:
            self.requires("xsimd/13.2.0")

    def validate(self):
        check_min_cppstd(self, self._min_cppstd)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            filename=f"apache-arrow-{self.version}.tar.gz", strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if cross_building(self):
            cmake_system_processor = {
                "armv8": "aarch64",
                "armv8.3": "aarch64",
            }.get(str(self.settings.arch), str(self.settings.arch))
            if cmake_system_processor == "aarch64":
                tc.variables["ARROW_CPU_FLAG"] = "armv8"
        # Arrow's SetupCxxFlags.cmake checks CMAKE_SYSTEM_PROCESSOR
        # OHOS CMake maps to HarmonyOS which resets CMAKE_SYSTEM_PROCESSOR to "unknown"
        # Setting ARROW_CPU_FLAG directly bypasses the detection logic
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["ARROW_CPU_FLAG"] = "aarch64"
        # Ensure libc++_shared.so can be found at runtime for shared deps
        # and — critically — for protoc / grpc_cpp_plugin to run at *build*
        # time (both are OHOS-native binaries linked against libc++_shared).
        sdk_llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        if os.path.isdir(sdk_llvm_lib):
            env = Environment()
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
            env.vars(self).save_script("libarrow_flight_runtime_env")

        tc.variables["ARROW_DEPENDENCY_SOURCE"] = "SYSTEM"
        tc.variables["ARROW_PACKAGE_KIND"] = "conan"
        tc.variables["ARROW_BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["ARROW_BUILD_STATIC"] = not bool(self.options.shared)
        tc.variables["ARROW_POSITION_INDEPENDENT_CODE"] = True

        # Core components
        tc.variables["ARROW_COMPUTE"] = bool(self.options.compute)
        tc.variables["ARROW_CSV"] = bool(self.options.csv)
        tc.variables["ARROW_FILESYSTEM"] = bool(self.options.filesystem_layer)
        tc.variables["ARROW_IPC"] = bool(self.options.ipc)
        tc.variables["ARROW_JSON"] = bool(self.options.json)

        # ⭐ FLIGHT is the primary component for this package.
        # ARROW_FLIGHT requires ARROW_IPC (see DefineOptions.cmake DEPENDS).
        tc.variables["ARROW_FLIGHT"] = True
        # Flight SQL extension (same gRPC stack, adds protobuf FlightSql.proto)
        tc.variables["ARROW_FLIGHT_SQL"] = bool(self.options.flight_sql)
        tc.variables["ARROW_FLIGHT_SQL_ODBC"] = False

        # Disabled components (dependencies not available or not needed)
        tc.variables["ARROW_PARQUET"] = False  # requires thrift (not published)
        tc.variables["ARROW_ORC"] = False
        tc.variables["ARROW_GANDIVA"] = False
        tc.variables["ARROW_CUDA"] = False
        tc.variables["ARROW_DATASET"] = False
        tc.variables["ARROW_ACERO"] = False
        tc.variables["ARROW_S3"] = False
        tc.variables["ARROW_GCS"] = False
        tc.variables["ARROW_HDFS"] = False
        tc.variables["ARROW_AZURE"] = False
        tc.variables["ARROW_SUBSTRAIT"] = False
        tc.variables["ARROW_PYTHON"] = False

        # Memory allocators
        tc.variables["ARROW_JEMALLOC"] = False
        tc.variables["ARROW_MIMALLOC"] = False

        # Build options
        tc.variables["ARROW_BUILD_TESTS"] = True
        tc.variables["ARROW_TESTING"] = True
        tc.variables["ARROW_BUILD_BENCHMARKS"] = False
        tc.variables["ARROW_BUILD_EXAMPLES"] = False
        tc.variables["ARROW_BUILD_INTEGRATION"] = False
        tc.variables["ARROW_BUILD_UTILITIES"] = False
        tc.variables["ARROW_ENABLE_TIMING_TESTS"] = False
        tc.variables["ARROW_BUILD_FUZZING_UTILITIES"] = False

        # Compression codecs
        tc.variables["ARROW_WITH_BROTLI"] = False
        tc.variables["ARROW_WITH_BZ2"] = bool(self.options.with_bz2)
        tc.variables["ARROW_WITH_LZ4"] = bool(self.options.with_lz4)
        tc.variables["ARROW_WITH_SNAPPY"] = bool(self.options.with_snappy)
        tc.variables["ARROW_WITH_ZLIB"] = bool(self.options.with_zlib)
        tc.variables["ARROW_WITH_ZSTD"] = bool(self.options.with_zstd)

        # Other dependencies
        tc.variables["ARROW_WITH_RE2"] = bool(self.options.with_re2)
        tc.variables["ARROW_WITH_UTF8PROC"] = bool(self.options.with_utf8proc)
        tc.variables["ARROW_USE_OPENSSL"] = bool(self.options.with_openssl)
        tc.variables["ARROW_WITH_BACKTRACE"] = False
        tc.variables["ARROW_WITH_OPENTELEMETRY"] = False
        tc.variables["ARROW_WITH_THRIFT"] = False

        # Boost
        if self.options.with_boost:
            tc.variables["ARROW_USE_BOOST"] = True
            tc.variables["ARROW_BOOST_USE_SHARED"] = False
            tc.variables["ARROW_BOOST_REQUIRED"] = True
        tc.variables["BOOST_SOURCE"] = "SYSTEM"

        # GTest
        tc.variables["GTest_SOURCE"] = "SYSTEM"
        tc.variables["GFlags_SOURCE"] = "SYSTEM"

        # Dependency source overrides (registry pre-built packages)
        tc.variables["brotli_SOURCE"] = "SYSTEM"
        tc.variables["BZip2_SOURCE"] = "SYSTEM"
        tc.variables["lz4_SOURCE"] = "SYSTEM"
        tc.variables["Snappy_SOURCE"] = "SYSTEM"
        tc.variables["ZLIB_SOURCE"] = "SYSTEM"
        tc.variables["zstd_SOURCE"] = "SYSTEM"
        tc.variables["re2_SOURCE"] = "SYSTEM"
        tc.variables["utf8proc_SOURCE"] = "SYSTEM"
        tc.variables["xsimd_SOURCE"] = "SYSTEM"
        tc.variables["RapidJSON_SOURCE"] = "SYSTEM"
        tc.variables["gflags_SOURCE"] = "SYSTEM"
        tc.variables["GLOG_SOURCE"] = "SYSTEM"
        tc.variables["SQLite3_SOURCE"] = "SYSTEM"
        # SQLite3: Arrow's FindSQLite3Alt is a MODULE-mode finder
        # (find_path/find_library) that never loads the CMakeDeps config.
        # Point it at the conan package layout directly.
        if self.options.flight_sql:
            sqlite3 = self.dependencies["sqlite3"]
            tc.variables["SQLite3_INCLUDE_DIR"] = os.path.join(
                sqlite3.package_folder, "include").replace("\\", "/")
            tc.variables["SQLite3_LIBRARY"] = os.path.join(
                sqlite3.package_folder, "lib", "libsqlite3.a").replace("\\", "/")

        # ⭐ gRPC + Protobuf: the registry grpc/1.70.0 package ships its own
        # component-rich CMake config (gRPCConfig.cmake with gRPC::grpc++ and
        # gRPC::grpc_cpp_plugin imported targets) and protobuf/33.6 ships
        # protobuf-config.cmake (protobuf::libprotobuf + protobuf::protoc).
        # Both recipes use cmake_find_mode=none, so Arrow's FindgRPCAlt /
        # FindProtobufAlt find_package(<name> CONFIG) lookups must be pointed
        # at the package folders explicitly (mirrors grpc's own recipe).
        # Protobuf_SOURCE / gRPC_SOURCE are left as SYSTEM (the default from
        # ARROW_DEPENDENCY_SOURCE) so the ARROW-15495 same-source constraint
        # (Protobuf_SOURCE == gRPC_SOURCE) holds and no FetchContent build
        # is attempted.
        grpc = self.dependencies["grpc"]
        tc.variables["gRPC_DIR"] = os.path.join(
            grpc.package_folder, "lib", "cmake", "grpc").replace("\\", "/")
        # Cross-compile: gRPCConfig.cmake only includes gRPCPluginTargets when
        # NOT CMAKE_CROSSCOMPILING, so the gRPC::grpc_cpp_plugin imported
        # target never exists on OHOS. Point Arrow's ARROW_GRPC_CPP_PLUGIN
        # at the registry plugin binary directly (it is an OHOS-native
        # arm64 executable that runs on this build host).
        tc.variables["ARROW_GRPC_CPP_PLUGIN"] = os.path.join(
            grpc.package_folder, "bin", "grpc_cpp_plugin").replace("\\", "/")
        protobuf = self.dependencies["protobuf"]
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf").replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range").replace("\\", "/")
        abseil = self.dependencies["abseil-cpp"]
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl").replace("\\", "/")

        # OpenSSL
        if self.options.with_openssl:
            tc.variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder.replace("\\", "/")
            tc.variables["ARROW_OPENSSL_USE_SHARED"] = bool(self.dependencies["openssl"].options.get_safe("shared", False))

        # SIMD
        tc.variables["ARROW_SIMD_LEVEL"] = str(self.options.simd_level).upper() if self.options.simd_level else "DEFAULT"
        tc.variables["ARROW_RUNTIME_SIMD_LEVEL"] = str(self.options.runtime_simd_level).upper() if self.options.runtime_simd_level else "MAX"

        # Build configuration
        tc.variables["BUILD_WARNING_LEVEL"] = "PRODUCTION"
        tc.variables["ARROW_INSTALL_NAME_RPATH"] = True
        tc.variables["ARROW_NO_DEPRECATED_API"] = False
        tc.variables["ARROW_VERBOSE_THIRDPARTY_BUILD"] = True

        tc.generate()

        deps = CMakeDeps(self)
        # Arrow's ThirdpartyToolchain.cmake expects specific target names that
        # differ from CMakeDeps defaults. Set cmake_target_name to match.
        deps.set_property("snappy", "cmake_target_name", "Snappy::snappy")
        deps.set_property("bzip2", "cmake_target_name", "BZip2::BZip2")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.set_property("lz4", "cmake_target_name", "LZ4::lz4")
        deps.set_property("zstd", "cmake_target_name", "zstd::libzstd_shared")
        deps.set_property("re2", "cmake_target_name", "re2::re2")
        deps.set_property("utf8proc", "cmake_target_name", "utf8proc::utf8proc")
        # NOTE: openssl is intentionally NOT remapped here. gRPC's shipped
        # gRPCTargets.cmake references the `openssl::openssl` imported target
        # (the CMakeDeps default for the openssl recipe). Arrow itself finds
        # OpenSSL through CMake's built-in FindOpenSSL (OPENSSL_ROOT_DIR is
        # set in the toolchain), so it doesn't need a remapped target either.
        deps.set_property("gflags", "cmake_target_name", "gflags::gflags")
        deps.set_property("rapidjson", "cmake_target_name", "RapidJSON::RapidJSON")
        deps.set_property("xsimd", "cmake_target_name", "xsimd")
        # SQLite3: Arrow's FindSQLite3Alt uses find_path/find_library directly;
        # CMakeDeps' default sqlite3-config sets SQLite3_INCLUDE_DIRS/LIBRARIES.
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "cpp"))
        cmake.build()

        # Execute upstream tests (ARROW_BUILD_TESTS=ON).
        # Arrow's add_test() wraps binaries with build-support/run-test.sh which
        # pushd's into per-test workdirs and pipes through python/c++filt —
        # both unavailable on the OHOS test device. Run each test binary
        # directly instead, collecting per-binary gtest results.
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        import re as _re

        release_dir = os.path.join(self.build_folder, "release")
        if not os.path.isdir(release_dir):
            self.output.warning("no test binaries found - skipping upstream tests")
            return

        # Dependency lib dirs for LD_LIBRARY_PATH (cross-compiled OHOS binaries
        # run natively on this aarch64 OHOS host but need their conan deps).
        deps_libs = [
            os.path.join(d.package_folder, "lib")
            for _r, d in self.dependencies.items()
            if d.package_folder
        ]
        sdk_libs = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        ]
        ld_path = ":".join(["/system/lib64"] + deps_libs + sdk_libs)

        test_results_dir = os.path.join(self.build_folder, "test_results")
        os.makedirs(test_results_dir, exist_ok=True)
        summary_path = os.path.join(test_results_dir, "test_summary.tsv")

        # Only run *-test binaries. Long-running helper servers
        # (flight-test-server, flight-sql-test-server) listen forever and
        # never exit on their own - they are test infrastructure, not tests.
        binaries = sorted(
            f for f in os.listdir(release_dir)
            if _re.match(r"^(arrow|flight)-.*-test$", f)
        )
        with open(summary_path, "w", encoding="utf-8") as summary:
            summary.write("test_binary\texit_code\tstatus\n")
            for t in binaries:
                logf = os.path.join(test_results_dir, f"{t}.log")
                # timeout guard: 600s per binary (Arrow suites finish in < 1min;
                # only a stuck server would hang - those are filtered above)
                cmd = (
                    f'LD_LIBRARY_PATH="{ld_path}" '
                    f'timeout 600 "{os.path.join(release_dir, t)}" > "{logf}" 2>&1'
                )
                try:
                    rc = self.run(cmd, cwd=release_dir, ignore_errors=True)
                    if rc in (None, True):
                        rc = 0
                    rc = int(rc)
                except Exception:
                    rc = -1
                if rc == 124:  # timeout(1) exit code
                    status = "TIMEOUT"
                elif rc == 0:
                    status = "PASS"
                else:
                    status = f"FAIL({rc})"
                summary.write(f"{t}\t{rc}\t{status}\n")
        self.output.info(f"upstream tests done: {len(binaries)} binaries, results in {summary_path}")

    def package(self):
        copy(self, pattern="LICENSE.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(self, pattern="NOTICE.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        # Ship the gRPC target bridge (grpc::grpc -> gRPC::grpc++) after the
        # rmdir cleanup: downstream CMakeDeps consumers include it via
        # cmake_build_modules so libarrow_flight's component references
        # resolve to the registry grpc package's native imported targets.
        # exports_sources files land next to the source tree root (with
        # cmake_layout(src_folder="src"), self.source_folder points at the
        # extracted src/ dir, while exported cmake/ sits one level up).
        bridge_src = None
        src_root = os.path.dirname(self.source_folder) if self.source_folder else None
        for cand in (
            os.path.join(src_root, "cmake") if src_root else None,
            os.path.join(self.source_folder or "", "cmake"),
            os.path.join(self.recipe_folder or "", "cmake"),
            self.export_sources_folder,
        ):
            if cand and os.path.isfile(os.path.join(cand, "bridge-grpc-targets.cmake")):
                bridge_src = cand
                break
        if bridge_src:
            copy(self, pattern="bridge-grpc-targets.cmake",
                 dst=os.path.join(self.package_folder, "lib", "cmake"),
                 src=bridge_src)
        else:
            self.output.warning("bridge-grpc-targets.cmake not found - grpc alias targets will not be created")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ArrowFlight")
        # The registry grpc package is cmake_find_mode=none (native config
        # exports gRPC::* targets); the bridge module creates the grpc::*
        # alias names used by this package's component references. CMakeDeps
        # consumers include it automatically.
        self.cpp_info.set_property("cmake_build_modules", [
            os.path.join("lib", "cmake", "bridge-grpc-targets.cmake")])

        cmake_suffix = "shared" if self.options.shared else "static"

        # Main Arrow library (built as part of flight build - arrow is a dependency)
        self.cpp_info.components["arrow"].set_property("pkg_config_name", "arrow")
        self.cpp_info.components["arrow"].set_property("cmake_file_name", "Arrow")
        self.cpp_info.components["arrow"].set_property("cmake_target_name", f"Arrow::arrow_{cmake_suffix}")
        self.cpp_info.components["arrow"].libs = ["arrow"]
        if not self.options.shared:
            self.cpp_info.components["arrow"].defines = ["ARROW_STATIC"]
            if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
                self.cpp_info.components["arrow"].system_libs = ["pthread", "m", "dl", "rt"]

        # Arrow compute library (separate target when compute is enabled)
        if self.options.compute:
            self.cpp_info.components["arrow_compute"].set_property("pkg_config_name", "arrow_compute")
            self.cpp_info.components["arrow_compute"].set_property("cmake_file_name", "Arrow")
            self.cpp_info.components["arrow_compute"].set_property("cmake_target_name", f"Arrow::arrow_compute_{cmake_suffix}")
            self.cpp_info.components["arrow_compute"].libs = ["arrow_compute"]
            self.cpp_info.components["arrow_compute"].requires = ["arrow"]
            if not self.options.shared:
                self.cpp_info.components["arrow_compute"].defines = ["ARROW_COMPUTE_STATIC"]

        # ⭐ Arrow Flight (gRPC data transport) - primary component of this package
        self.cpp_info.components["arrow_flight"].set_property("pkg_config_name", "arrow-flight")
        self.cpp_info.components["arrow_flight"].set_property("cmake_file_name", "ArrowFlight")
        self.cpp_info.components["arrow_flight"].set_property("cmake_target_name", f"ArrowFlight::arrow_flight_{cmake_suffix}")
        self.cpp_info.components["arrow_flight"].libs = ["arrow_flight"]
        self.cpp_info.components["arrow_flight"].requires = ["arrow"]
        if self.options.compute:
            self.cpp_info.components["arrow_flight"].requires.append("arrow_compute")
        if not self.options.shared:
            self.cpp_info.components["arrow_flight"].defines = ["ARROW_FLIGHT_STATIC", "ARROW_STATIC"]
            if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
                self.cpp_info.components["arrow_flight"].system_libs = ["pthread", "m", "dl", "rt"]
        # Flight is gRPC-based: propagate grpc/protobuf to consumers.
        # The registry grpc package is component-rich (cmake_find_mode=none)
        # and its native config exports gRPC::grpc++; conan component
        # references must be pkgname::x, so we reference grpc::grpc++ and
        # ship lib/cmake/bridge-grpc-targets.cmake which creates that alias
        # from gRPC::grpc++ (included automatically via cmake_build_modules).
        # protobuf/33.6's native config exports protobuf::libprotobuf etc.;
        # protobuf::protobuf matches the conan package-level target it also
        # declares.
        self.cpp_info.components["arrow_flight"].requires.append("grpc::grpc")
        self.cpp_info.components["arrow_flight"].requires.append("protobuf::protobuf")

        # Arrow Flight SQL extension
        if self.options.flight_sql:
            self.cpp_info.components["arrow_flight_sql"].set_property("pkg_config_name", "arrow-flight-sql")
            self.cpp_info.components["arrow_flight_sql"].set_property("cmake_file_name", "ArrowFlightSQL")
            self.cpp_info.components["arrow_flight_sql"].set_property("cmake_target_name", f"ArrowFlightSQL::arrow_flight_sql_{cmake_suffix}")
            self.cpp_info.components["arrow_flight_sql"].libs = ["arrow_flight_sql"]
            self.cpp_info.components["arrow_flight_sql"].requires = ["arrow_flight"]
            # sqlite3 powers the Flight SQL test-server/example shipped with
            # the source tree (upstream builds it whenever ARROW_FLIGHT_SQL
            # tests are enabled); keep it declared on the component.
            self.cpp_info.components["arrow_flight_sql"].requires.append("sqlite3::sqlite3")
            if not self.options.shared:
                self.cpp_info.components["arrow_flight_sql"].defines = ["ARROW_FLIGHT_SQL_STATIC", "ARROW_FLIGHT_STATIC", "ARROW_STATIC"]

        # Dependency propagation
        if self.options.with_boost:
            self.cpp_info.components["arrow"].requires.append("boost::boost")
        if self.options.with_openssl:
            self.cpp_info.components["arrow"].requires.append("openssl::openssl")
        if self.options.with_re2:
            self.cpp_info.components["arrow"].requires.append("re2::re2")
        if self.options.with_utf8proc:
            self.cpp_info.components["arrow"].requires.append("utf8proc::utf8proc")
        if self.options.with_bz2:
            self.cpp_info.components["arrow"].requires.append("bzip2::bzip2")
        if self.options.with_lz4:
            self.cpp_info.components["arrow"].requires.append("lz4::lz4")
        if self.options.with_snappy:
            self.cpp_info.components["arrow"].requires.append("snappy::snappy")
        if self.options.with_zlib:
            self.cpp_info.components["arrow"].requires.append("zlib::zlib")
        if self.options.with_zstd:
            self.cpp_info.components["arrow"].requires.append("zstd::zstd")
        if self.options.json:
            self.cpp_info.components["arrow"].requires.append("rapidjson::rapidjson")
        if self.options.get_safe("simd_level") is not None or self.options.get_safe("runtime_simd_level") is not None:
            self.cpp_info.components["arrow"].requires.append("xsimd::xsimd")
