import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir, save
from conan.tools.scm import Version

required_conan_version = ">=2.1.0"


class LibarrowAceroConan(ConanFile):
    name = "libarrow_acero"
    version = "23.0.1"
    description = "Apache Arrow Acero - streaming compute engine (Arrow Compute Engine)"
    license = ("Apache-2.0",)
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    homepage = "https://arrow.apache.org/"
    topics = ("arrow", "acero", "compute", "streaming", "engine", "aarch64")
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
        "with_brotli": [True, False],
        "with_bz2": [True, False],
        "with_lz4": [True, False],
        "with_snappy": [True, False],
        "with_zlib": [True, False],
        "with_zstd": [True, False],
        "with_re2": [True, False],
        "with_utf8proc": [True, False],
        "with_openssl": [True, False],
        "with_gflags": [True, False],
        "with_glog": [True, False],
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
        "with_brotli": False,
        "with_bz2": True,
        "with_lz4": True,
        "with_snappy": True,
        "with_zlib": True,
        "with_zstd": True,
        "with_re2": True,
        "with_utf8proc": True,
        "with_openssl": True,
        "with_gflags": False,
        "with_glog": False,
        "simd_level": "default",
        "runtime_simd_level": "max",
    }

    short_paths = True

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

    def layout(self):
        cmake_layout(self, src_folder="src")

    def build_requirements(self):
        if self.settings.os in ("Linux", "OHOS"):
            # GTest needed for ARROW_BUILD_TESTS=ON (upstream test execution)
            # gflags is required by Arrow when ARROW_BUILD_TESTS=ON (for integration tests)
            self.test_requires("gtest/1.17.0.1")
            self.test_requires("gflags/2.2.2.1")

    def requirements(self):
        if self.options.with_boost:
            self.requires("boost/1.84.0")
        if self.options.with_brotli:
            self.requires("brotli/1.2.0")
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
            self.requires("openssl/3.0.16")
        if self.options.with_glog:
            self.requires("glog/0.7.1")
        if self.options.with_gflags:
            self.requires("gflags/2.2.2")
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
        sdk_llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        import os as _os
        if _os.path.isdir(sdk_llvm_lib):
            env = Environment()
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
            env.vars(self).save_script("libarrow_acero_runtime_env")

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

        # ⭐ ACERO is the primary component for this package
        tc.variables["ARROW_ACERO"] = True

        # Disabled components (dependencies not available or not needed)
        tc.variables["ARROW_PARQUET"] = False  # requires thrift (not published)
        tc.variables["ARROW_FLIGHT"] = False
        tc.variables["ARROW_FLIGHT_SQL"] = False
        tc.variables["ARROW_ORC"] = False
        tc.variables["ARROW_GANDIVA"] = False
        tc.variables["ARROW_CUDA"] = False
        tc.variables["ARROW_DATASET"] = False  # depends on acero, but separate component
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
        tc.variables["ARROW_WITH_BROTLI"] = bool(self.options.with_brotli)
        tc.variables["ARROW_WITH_BZ2"] = bool(self.options.with_bz2)
        tc.variables["ARROW_WITH_LZ4"] = bool(self.options.with_lz4)
        tc.variables["ARROW_WITH_SNAPPY"] = bool(self.options.with_snappy)
        tc.variables["ARROW_WITH_ZLIB"] = bool(self.options.with_zlib)
        tc.variables["ARROW_WITH_ZSTD"] = bool(self.options.with_zstd)

        # Other dependencies
        tc.variables["ARROW_WITH_RE2"] = bool(self.options.with_re2)
        tc.variables["ARROW_WITH_UTF8PROC"] = bool(self.options.with_utf8proc)
        tc.variables["ARROW_USE_OPENSSL"] = bool(self.options.with_openssl)
        tc.variables["ARROW_USE_GLOG"] = bool(self.options.with_glog)
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

        # Dependency source overrides
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
        deps.set_property("openssl", "cmake_target_name", "OpenSSL::SSL")
        deps.set_property("gflags", "cmake_target_name", "gflags::gflags")
        deps.set_property("rapidjson", "cmake_target_name", "RapidJSON::RapidJSON")
        deps.set_property("xsimd", "cmake_target_name", "xsimd")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "cpp"))
        cmake.build()

        # Execute upstream tests (ARROW_BUILD_TESTS=ON, 66 ctest targets).
        # Arrow's add_test() wraps binaries with build-support/run-test.sh which
        # pushd's into per-test workdirs and pipes through python/c++filt —
        # both unavailable on the OHOS test device. Run each test binary
        # directly instead, collecting per-binary gtest results.
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        import glob as _glob
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

        binaries = sorted(
            f for f in os.listdir(release_dir)
            if _re.match(r"^arrow-.*-test$", f)
        )
        with open(summary_path, "w", encoding="utf-8") as summary:
            summary.write("test_binary\texit_code\tstatus\n")
            for t in binaries:
                logf = os.path.join(test_results_dir, f"{t}.log")
                cmd = (
                    f'LD_LIBRARY_PATH="{ld_path}" '
                    f'"{os.path.join(release_dir, t)}" > "{logf}" 2>&1'
                )
                try:
                    rc = self.run(cmd, cwd=release_dir, ignore_errors=True)
                    if rc in (None, True):
                        rc = 0
                    rc = int(rc)
                except Exception:
                    rc = -1
                status = "PASS" if rc == 0 else f"FAIL({rc})"
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

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Arrow")

        cmake_suffix = "shared" if self.options.shared else "static"

        # Main Arrow library (built as part of acero build - arrow is a dependency)
        self.cpp_info.components["arrow"].set_property("pkg_config_name", "arrow")
        self.cpp_info.components["arrow"].set_property("cmake_target_name", f"Arrow::arrow_{cmake_suffix}")
        self.cpp_info.components["arrow"].libs = ["arrow"]
        if not self.options.shared:
            self.cpp_info.components["arrow"].defines = ["ARROW_STATIC"]
            if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
                self.cpp_info.components["arrow"].system_libs = ["pthread", "m", "dl", "rt"]

        # Arrow compute library (separate target when compute is enabled)
        if self.options.compute:
            self.cpp_info.components["arrow_compute"].set_property("pkg_config_name", "arrow_compute")
            self.cpp_info.components["arrow_compute"].set_property("cmake_target_name", f"Arrow::arrow_compute_{cmake_suffix}")
            self.cpp_info.components["arrow_compute"].libs = ["arrow_compute"]
            self.cpp_info.components["arrow_compute"].requires = ["arrow"]
            if not self.options.shared:
                self.cpp_info.components["arrow_compute"].defines = ["ARROW_COMPUTE_STATIC"]

        # ⭐ Arrow Acero (streaming compute engine) - primary component of this package
        self.cpp_info.components["arrow_acero"].set_property("pkg_config_name", "arrow_acero")
        self.cpp_info.components["arrow_acero"].set_property("cmake_target_name", f"Arrow::arrow_acero_{cmake_suffix}")
        self.cpp_info.components["arrow_acero"].libs = ["arrow_acero"]
        self.cpp_info.components["arrow_acero"].requires = ["arrow"]
        if self.options.compute:
            self.cpp_info.components["arrow_acero"].requires.append("arrow_compute")
        if not self.options.shared:
            self.cpp_info.components["arrow_acero"].defines = ["ARROW_STATIC"]

        # Dependency propagation
        if self.options.with_boost:
            self.cpp_info.components["arrow"].requires.append("boost::boost")
        if self.options.with_openssl:
            self.cpp_info.components["arrow"].requires.append("openssl::openssl")
        if self.options.with_gflags:
            self.cpp_info.components["arrow"].requires.append("gflags::gflags")
        if self.options.with_glog:
            self.cpp_info.components["arrow"].requires.append("glog::glog")
        if self.options.with_re2:
            self.cpp_info.components["arrow"].requires.append("re2::re2")
        if self.options.with_utf8proc:
            self.cpp_info.components["arrow"].requires.append("utf8proc::utf8proc")
        if self.options.with_brotli:
            self.cpp_info.components["arrow"].requires.append("brotli::brotli")
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
