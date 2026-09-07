#!/usr/bin/env python3
"""Conan recipe for broker 1.4.0 (Zeek's in-process pub-sub message broker).

Broker (https://github.com/zeek/broker) is a C++17 library implementing a
message broker: in-process pub-sub with an optional network transport built
on the C++ Actor Framework (CAF). Build system is CMake; the product is the
libbroker static/shared library.

Dependency handling (CAF, W0 evidence):
  The ohpcd artifact registry already publishes actor-framework/0.17.6
  (the conan-center name of CAF). However broker 1.4.0 cannot consume that
  package:
    - broker/CMakeLists.txt does find_package(CAF COMPONENTS openssl test
      io core REQUIRED) when building against an external CAF (CAF_ROOT_DIR),
      i.e. it also needs libcaf_openssl and libcaf_test.
    - The published actor-framework/0.17.6 recipe hard-codes CAF_NO_OPENSSL=ON
      and exposes only core+io components (no openssl/test), and it exports
      its CMake config as "actor-framework" instead of CAFConfig.
  Broker upstream officially vendors CAF as a git submodule pinned to
  zeek/actor-framework commit f7d4fc7ac (v1.4.0's caf/). We verified with
  `diff -rq` that the tree of that pinned commit is byte-identical to the
  upstream 0.17.6 release tarball (0 differing files). This recipe therefore
  follows the upstream-supported build: the pinned submodule sources are
  bundled in-tree and built via add_subdirectory(caf) (the code path broker
  uses when CAF_ROOT_DIR is unset). The broker tag tarball does not contain
  the submodule contents, so conandata.yml carries the three submodule
  source archives pinned by v1.4.0 (.gitmodules): caf (zeek/actor-framework
  @ f7d4fc7ac), cmake (zeek/cmake @ 153496b, provides
  CommonCMakeConfig.cmake), and 3rdparty (zeek-zeek-3rdparty @ bc5e6ab:
  sqlite3 amalgamation used by the store backend + doctest.h).

Upstream tests (C++ suites under tests/cpp/, registered by
tests/CMakeLists.txt as CTest cases that run the broker-test binary with a
suite selector) are executed in build() via ctest. Python-binding suites are
not built because DISABLE_PYTHON_BINDINGS is set on OHOS (the pybind11
submodule is intentionally not bundled; upstream also skips them when no
Python dev stack is available).

Test counts (five-place sync: conanfile docstring / test_package MANIFEST.yml
/ test_package CMakeLists comment / test source comment / PR description):
  - upstream: 22 CTest suites, all green on OHOS (conan create build() phase)
  - added consumer tests: 7 cases / 30 assertions in test_package/
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class BrokerConan(ConanFile):
    name = "broker"
    version = "1.4.0"
    description = "Zeek's message broker - an in-process pub-sub message bus"
    license = "BSD-3-Clause"
    homepage = "https://github.com/zeek/broker"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
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

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"broker supports Linux and OHOS, not {self.settings.os}"
            )
        check_min_cppstd(self, "17")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1")

    def environment(self):
        # lld lives in the OHOS SDK llvm dir; at runtime it needs
        # libxml2.so.16 which is not on the default loader path (observed in
        # CI/this machine: 'Error loading shared library libxml2.so.16' when
        # CMake runs compiler-link checks). Inject that dir, mirroring the
        # absl recipe pattern.
        env = Environment()
        env.append_path(
            "LD_LIBRARY_PATH",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib")
        return env

    def source(self):
        data = self.conan_data["sources"]
        # Main repo (tag tarball; the caf/ cmake/ 3rdparty submodule dirs are
        # empty placeholders inside the GitHub archive and are filled below).
        get(self, url=data["broker"]["url"], sha256=data["broker"]["sha256"],
            strip_root=True)
        # CAF fork pinned by broker v1.4.0 (tree == actor-framework 0.17.6,
        # verified by tree diff).
        get(self, url=data["caf"]["url"], sha256=data["caf"]["sha256"],
            destination="caf", strip_root=True)
        # zeek/cmake submodule: shared CMake modules of the zeek project.
        get(self, url=data["cmake"]["url"], sha256=data["cmake"]["sha256"],
            destination="cmake", strip_root=True)
        # zeek-3rdparty submodule: sqlite3 amalgamation + doctest.h.
        get(self, url=data["3rdparty"]["url"],
            sha256=data["3rdparty"]["sha256"],
            destination="3rdparty", strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["ENABLE_STATIC_ONLY"] = not bool(self.options.shared)
        # Broker's own logic maps ENABLE_STATIC_ONLY to CAF_BUILD_STATIC (not
        # CAF_BUILD_STATIC_ONLY), which would leave shared CAF libs. Force the
        # static-only variant directly so no runtime loader deps remain.
        tc.cache_variables["CAF_BUILD_STATIC_ONLY"] = not bool(
            self.options.shared)
        tc.cache_variables["BROKER_DISABLE_TOOLS"] = True
        tc.cache_variables["BROKER_DISABLE_DOCS"] = True
        tc.cache_variables["BROKER_DISABLE_TESTS"] = False
        tc.cache_variables["DISABLE_PYTHON_BINDINGS"] = True
        # find_package(OpenSSL) must resolve to the conan openssl package and
        # not to any host-installed OpenSSL (this machine ships a Homebrew
        # openssl under ~/.harmonybrew that FindOpenSSL otherwise prefers).
        openssl_dir = self.dependencies["openssl"].package_folder
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = os.path.join(
            openssl_dir, "include")
        # crypto listed before ssl: broker links static archives in order and
        # libcaf_openssl_static (scanned earlier) resolves against these.
        tc.cache_variables["OPENSSL_LIBRARIES"] = ";".join([
            os.path.join(openssl_dir, "lib", "libcrypto.a"),
            os.path.join(openssl_dir, "lib", "libssl.a"),
        ])
        tc.cache_variables["OPENSSL_ROOT_DIR"] = openssl_dir
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        self.run(
            'cmake --build "%s" -- -j4' % self.build_folder,
            env="conanbuild",
        )
        # Upstream C++ unit-test suites (registered via tests/CMakeLists.txt:
        # each CTest case runs broker-test with a CAF suite selector).
        if can_run(self) and not self.conf.get(
                "user.broker:skip_tests", default=False, check_type=bool):
            # The OHOS sandbox keeps /tmp read-only; upstream's temp-file
            # helper honors $TMPDIR (patches/0001-...), so point it at a
            # writable dir inside the build tree.
            tmpdir = os.path.join(self.build_folder, "tmp")
            self.run(
                'mkdir -p "%s" && TMPDIR="%s" ctest --test-dir "%s" '
                '--output-on-failure -j1 --timeout 60'
                % (tmpdir, tmpdir, self.build_folder),
                env="conanbuild",
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # License files (broker ships COPYING; CAF ships LICENSE).
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "LICENSE*", src=os.path.join(self.source_folder, "caf"),
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # Keep the package a pure library: drop anything tests/CMakeLists.txt
        # installed into bin/ (benchmark executables).
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for name in os.listdir(bin_dir):
                os.remove(os.path.join(bin_dir, name))
            os.rmdir(bin_dir)
        # Headers of the bundled CAF (caf/ source tree), merged under
        # include/caf as broker consumers use <caf/...> includes.
        for caf_component in ("core", "io", "openssl", "test"):
            src = os.path.join(self.source_folder, "caf",
                               "libcaf_%s" % caf_component, "caf")
            if os.path.isdir(src):
                copy(self, "*.hpp", src=src,
                     dst=os.path.join(self.package_folder, "include"),
                     keep_path=False)
        # CAF build-generated headers (build_config.hpp etc.).
        caf_build_inc = os.path.join(self.build_folder, "caf")
        for sub in ("libcaf_core", "libcaf_io", "libcaf_openssl",
                    "libcaf_test"):
            gen = os.path.join(caf_build_inc, sub, "caf", "detail")
            if os.path.isdir(gen):
                copy(self, "*.hpp", src=gen,
                     dst=os.path.join(self.package_folder, "include", "caf",
                                      "detail"),
                     keep_path=False)
        # CAF libraries built inside the broker build tree (static-only).
        lib_dir = os.path.join(self.build_folder, "lib")
        if self.options.get_safe("shared"):
            for libname in ("libcaf_openssl.so", "libcaf_io.so",
                            "libcaf_core.so"):
                if os.path.exists(os.path.join(lib_dir, libname)):
                    copy(self, libname, src=lib_dir,
                         dst=os.path.join(self.package_folder, "lib"),
                         keep_path=False)
        else:
            for libname in ("libcaf_openssl_static.a", "libcaf_io_static.a",
                            "libcaf_core_static.a", "libcaf_test_static.a"):
                if os.path.exists(os.path.join(lib_dir, libname)):
                    copy(self, libname, src=lib_dir,
                         dst=os.path.join(self.package_folder, "lib"),
                         keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "broker")
        if self.options.shared:
            self.cpp_info.libs = ["broker", "caf_openssl", "caf_io",
                                  "caf_core"]
        else:
            self.cpp_info.libs = ["broker", "caf_openssl_static",
                                  "caf_io_static", "caf_core_static"]
        self.cpp_info.requires = ["openssl::openssl"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
