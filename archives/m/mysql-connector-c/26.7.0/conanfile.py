#!/usr/bin/env python3
"""Conan recipe — mysql-connector-c (MySQL Connector/C++) 26.7.0 on OHOS PC.

All build-time CMake variables, including the OpenSSL include/library
paths, are derived from the Conan dependency graph
(self.dependencies["openssl"]) and written to conan_toolchain.cmake
via CMakeToolchain.cache_variables. No filesystem path is hardcoded so
the recipe is portable across hosts and the CI sandbox.

Build profile: ohos-aarch64 (see ci/conan/build_and_test.sh).
Target product: libmysqlcppconnx-static.a (BUILD_STATIC=ON, BUILD_SHARED_LIBS=OFF).

The MySQL Connector/C++ 26.7.0 upstream CMakeLists.txt invokes an
internal `bootstrap()` (cdk/cmake/bootstrap.cmake) which spawns a child
CMake configure of cdk/cmake/bootstrap/ and then calls
`load_cache(... INCLUDE_INTERNALS ...)` on the result. That load_cache
step overrides the values previously set by the Conan toolchain
(BUILD_STATIC, WITH_SSL, etc.), reverting BUILD_STATIC to OFF and
WITH_SSL to "system". This breaks the Conan-managed configure.
We follow the Conan Center Index reference recipe and disable the
upstream bootstrap() via replace_in_file, which is the standard
recipe-source-fix pattern used elsewhere in this repository (see e.g.
archives/a/acme-client/0.1.15-portable/conanfile.py).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MysqlconnectorcConan(ConanFile):
    name = "mysql-connector-c"
    version = "26.7.0"
    description = "mysql-connector-c 26.7.0"
    license = "GPL-2.0"
    homepage = "https://github.com/mysql/mysql-connector-cpp"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # conandata.yml `sources:` is a flat mapping with url/sha256.
        # Using `**self.conan_data["sources"]` is dangerous because it
        # would forward `url` and `sha256` as separate kwargs into
        # conan.tools.files.get, where `url` would become a positional
        # download target while `sha256` is passed as a positional
        # `filename` argument.  Conan then tries to decode a JSON
        # error response as metadata, raising JSONDecodeError.
        src = self.conan_data["sources"]
        get(
            self,
            url=src["url"],
            sha256=src["sha256"],
            strip_root=True,
        )
        self._patch_sources()

    def _patch_sources(self):
        # Disable upstream bootstrap() call.
        # The bootstrap() function in cdk/cmake/bootstrap.cmake spawns a
        # child CMake configure and then calls load_cache() to merge the
        # child project's internal variables into the parent cache. The
        # child project does not set BUILD_STATIC / WITH_SSL, so its
        # defaults (OFF / system) clobber the values we set here via
        # CMakeToolchain.cache_variables. Same approach as the official
        # Conan Center Index recipe for mysql-connector-cpp (see
        # recipes/mysql-connector-cpp/all/conanfile.py in conan-center-index).
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "bootstrap()",
            "",
        )

    def generate(self):
        tc = CMakeToolchain(self)

        # ── Static build target product: libmysqlcppconnx-static.a ──
        # BUILD_STATIC is the master switch in upstream CMakeLists.txt;
        # BUILD_SHARED_LIBS forces libutils.cmake to pick the matching
        # library type. Both values are set via cache_variables (the
        # Conan 2 preferred API). cache_variables are passed on the
        # cmake command line as -D<var>=<value>, which is overridden
        # by the cmake cache only if the cache sets a normal variable
        # with no type — that is not the case here.
        #
        # `self.options.shared` semantics:
        #   True  → user requested shared, BUILD_SHARED_LIBS=ON, BUILD_STATIC=OFF
        #   False → user requested static, BUILD_SHARED_LIBS=OFF, BUILD_STATIC=ON
        # Our default is shared=False, so by default we produce the
        # static library. The CI must invoke `conan create ... -o
        # mysql-connector-c:shared=True` to switch to shared.
        tc.cache_variables["BUILD_STATIC"] = not self.options.shared
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)

        # Disable JDBC (requires Java on OHOS) and upstream test suites
        # (GTest). WITH_TESTS=OFF; GTest migration is a follow-up task
        # once the main library CI is green.
        tc.cache_variables["WITH_JDBC"] = False
        tc.cache_variables["WITH_TESTS"] = False
        tc.cache_variables["WITH_PACKAGES"] = False

        # ── OpenSSL: take all paths from the Conan dependency graph ──
        # The upstream cdk/cmake/DepFindSSL.cmake defines
        #   add_config_option(WITH_SSL STRING DEFAULT system ...)
        # and when WITH_SSL is not "system" or "yes" it forwards the
        # value as both OPENSSL_ROOT_DIR and OpenSSL_DIR to a native
        # find_package(OpenSSL) call. Passing the openssl package folder
        # here steers DepFindSSL to the Conan-installed library and
        # bypasses the broken system-search path on OHOS.
        openssl_pkg = self.dependencies["openssl"].package_folder
        openssl_pkg_posix = openssl_pkg.replace("\\", "/")
        openssl_lib = os.path.join(openssl_pkg, "lib")
        openssl_inc = os.path.join(openssl_pkg, "include")

        tc.cache_variables["WITH_SSL"] = openssl_pkg_posix
        tc.cache_variables["OPENSSL_ROOT_DIR"] = openssl_pkg_posix
        tc.cache_variables["OpenSSL_DIR"] = openssl_pkg_posix
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = openssl_inc
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = os.path.join(
            openssl_lib, "libssl.a"
        )
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(
            openssl_lib, "libcrypto.a"
        )
        tc.cache_variables["OPENSSL_FOUND"] = "TRUE"
        tc.cache_variables["OPENSSL_USE_STATIC_LIBS"] = True

        # Expose the conan generators folder to the main cmake configure
        # so it can find any auxiliary find_package configs emitted by
        # CMakeDeps.
        tc.cache_variables["CMAKE_PREFIX_PATH"] = self.generators_folder.replace(
            "\\", "/"
        )

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
        # The upstream CMakeLists.txt (install_layout.cmake) sets
        # LIB_NAME_STATIC = "mysqlcppconnx-static", and the package step
        # runs cmake.install() which copies libmysqlcppconnx-static.a
        # (or libmysqlcppconnx.so) into the package's lib/ directory.
        # Conan's CMakeDeps builds the consumer-facing target
        # (mysql-connector-c::mysql-connector-c) using
        # self.cpp_info.libs as the link library list, so the list must
        # match the actual archive basenames.
        if self.options.shared:
            self.cpp_info.libs = ["mysqlcppconnx"]
        else:
            self.cpp_info.libs = ["mysqlcppconnx-static"]
        # The upstream header mysqlx/common/api.h uses STATIC_CONCPP
        # (set by the upstream CMakeLists.txt at line 629 when
        # BUILD_STATIC=ON) to choose PUBLIC_API=DLL_IMPORT vs. empty.
        # When consumers (test_package, downstream conan consumers)
        # link the static archive, they must define this macro so
        # the connector's public symbols are not marked DLL_IMPORT.
        # We forward the macro to consumers via self.cpp_info.defines
        # (the upstream-installed mysql-concpp-config.cmake would
        # otherwise set this, but here we are responsible for the
        # consumer-facing metadata).
        if not self.options.shared:
            self.cpp_info.defines = ["STATIC_CONCPP"]
        # The package installs headers under include/jdbc and
        # include/mysqlx. Tell consumers to look in include/ (the
        # upstream root) so the test_package can use
        # <mysqlx/xapi.h> directly.
        self.cpp_info.includedirs = ["include"]
