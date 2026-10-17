#!/usr/bin/env python3
"""Conan recipe for rocksdb 11.1.2 — CMake build system.

RocksDB is a high-performance embedded key-value store by Meta.

This recipe adapts **11.1.2** from scratch (the 9.10.0 archive in this repo
only carries manifest/notes/patches — it never had a conanfile.py, so nothing
could be copied).  Re-verified against the 11.1.2 source tree:

OHOS adaptation notes:
  - `env/fs_posix.cc` / `env/io_posix.cc` need `<sys/statfs.h>` and
    `<sys/sysmacros.h>`, but the guard is `#if defined(OS_LINUX) || ...`.
    RocksDB derives OS_LINUX from `CMAKE_SYSTEM_NAME MATCHES "Linux"`
    (CMakeLists.txt:516-517) and has no OHOS branch, so under an OHOS
    toolchain OS_LINUX is undefined and the headers never get included.
    The two portability patches widen the guard with `|| defined(__OHOS__)`
    (the compiler-provided macro).  Both patches apply to 11.1.2 with zero
    fuzz (verified with `patch -p1 --dry-run`, hunks land at
    env/fs_posix.cc:27 and env/io_posix.cc:31).
  - `FAIL_ON_WARNINGS` defaults ON in 11.1.2 (CMakeLists.txt:370); disabled
    here because OHOS clang 15 emits warnings upstream never saw.
  - `PORTABLE=1` is passed defensively: with PORTABLE=0 (the default) and a
    failed `-march=armv8-a+crc+crypto` probe (CMakeLists.txt:268-275),
    CMakeLists.txt:303-316 would inject `-march=native`, which clang rejects
    for a cross target.
  - Cross-compile safety: `WITH_TESTS` defaults to
    `CMAKE_DEPENDENT_OPTION(... ON "CMAKE_BUILD_TYPE STREQUAL Debug" OFF)`
    (CMakeLists.txt:1234).  In Release it is OFF, which is required here
    because `gtest_discover_tests()` (CMakeLists.txt:1604) executes the
    freshly linked aarch64 test binaries at build time.  We force it OFF
    explicitly rather than rely on the build type.
  - `WITH_LIBURING` defaults ON (CMakeLists.txt:92).  liburing is not
    available for OHOS on the registry, and the `find_package(uring)` probe
    (CMakeLists.txt:349-355) is non-REQUIRED, but we turn it OFF explicitly
    so the probe never runs and `-DROCKSDB_IOURING_PRESENT` is never set.
  - `WITH_GFLAGS` defaults ON (CMakeLists.txt:133); gflags is not needed by
    any consumer here and is not required for the library itself, so it is
    turned OFF.  The `gflags` CLI flags only affect db_bench/db_stress.
  - zstd is intentionally NOT enabled: the only zstd on the registry
    (`zstd/1.5.7.1`) is published **shared-only**, and the OHOS dynamic
    loader rejects shared libraries living under user-writable paths, which
    would break test_package.  zlib / snappy / lz4 / bzip2 are all published
    static and give RocksDB real compression support.

Compression dependencies (all published on the HarmonyOS registry, static):
  zlib/1.3.1, snappy/1.2.2, lz4/1.10.0, bzip2/1.0.8
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class RocksdbConan(ConanFile):
    name = "rocksdb"
    version = "11.1.2"
    description = "High-performance embedded key-value store for fast storage (Meta)"
    license = "Apache-2.0"
    homepage = "https://rocksdb.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("snappy/1.2.2")
        self.requires("lz4/1.10.0")
        self.requires("bzip2/1.0.8")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # verify=False: the OHOS build env lacks a usable CA bundle for curl;
        # the SHA256 in conandata.yml is still enforced by Conan's cache.
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # Ninja generator: /bin/sh is not usable by the default Unix Makefiles
        # generator in the OHOS container.
        tc = CMakeToolchain(self, generator="Ninja")
        # RocksDB only defaults CMAKE_CXX_STANDARD to 20 when it is NOT already
        # defined (CMakeLists.txt:103-105).  The CI profile pins cppstd=17, so
        # Conan's toolchain defines CMAKE_CXX_STANDARD=17 and RocksDB keeps it:
        # util/bit_fields.h then fails with
        #   "defaulted comparison operators are a C++20 extension"
        #   error: invalid operands to binary expression (BitFields != BitFields)
        # Set it explicitly here so the profile cannot hold the build back.
        tc.variables["CMAKE_CXX_STANDARD"] = 20
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        # ── compression codecs (registry packages, static) ──────────────
        tc.variables["WITH_ZLIB"] = "ON"
        tc.variables["WITH_SNAPPY"] = "ON"
        tc.variables["WITH_LZ4"] = "ON"
        tc.variables["WITH_BZ2"] = "ON"
        tc.variables["WITH_ZSTD"] = "OFF"   # registry zstd is shared-only
        # ── not available / not needed on OHOS ──────────────────────────
        tc.variables["WITH_GFLAGS"] = "OFF"
        tc.variables["WITH_LIBURING"] = "OFF"
        tc.variables["WITH_JEMALLOC"] = "OFF"
        # ── library only: no tests, tools, benches, examples ────────────
        tc.variables["WITH_TESTS"] = "OFF"
        tc.variables["WITH_ALL_TESTS"] = "OFF"
        tc.variables["WITH_TOOLS"] = "OFF"
        tc.variables["WITH_CORE_TOOLS"] = "OFF"
        tc.variables["WITH_BENCHMARK_TOOLS"] = "OFF"
        tc.variables["WITH_EXAMPLES"] = "OFF"
        tc.variables["WITH_BENCHMARK"] = "OFF"
        tc.variables["WITH_JNI"] = "OFF"
        # ── portability / warnings ──────────────────────────────────────
        tc.variables["FAIL_ON_WARNINGS"] = "OFF"
        tc.variables["PORTABLE"] = "1"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # RocksDB does NOT derive its shared target from BUILD_SHARED_LIBS: it
        # has its own option, `option(ROCKSDB_BUILD_SHARED ... ON)`
        # (CMakeLists.txt:101), so with shared=False the build still produced
        # librocksdb.so and linked the static dependencies into it.
        #
        # That link is what the CI rejected:
        #   FAILED: librocksdb.so
        #   ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used
        #   against symbol 'z_errmsg'; recompile with -fPIC
        #     defined in .../p/zlib56af09fbb4346/p/lib/libz.a(zutil.o)
        # The registry's zlib static archive is not PIC, so it can go into an
        # executable but not into a shared object.  Building the static library
        # only (the default) avoids the shared link entirely.
        tc.variables["ROCKSDB_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["rocksdb"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
