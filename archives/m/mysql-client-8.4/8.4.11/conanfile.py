#!/usr/bin/env python3
"""Conan recipe for MySQL 8.4 client library and client tools (OHOS port).

Client-only build (WITHOUT_SERVER=ON) of the upstream MySQL 8.4 LTS series,
following the ConanCenter-style pure-client packaging (libmysqlclient) under
the dedicated mysql-client-8.4 package name. The bundled Boost headers
(boost_1_84_0) ship inside the source tarball, so no external Boost
dependency is needed. See notes.md for the porting story and patches/ for
the OHOS-specific modifications.
"""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rmdir,
)


class MysqlClient84Conan(ConanFile):
    name = "mysql-client-8.4"
    version = "8.4.11"
    description = "MySQL 8.4 LTS client library and client tools for OHOS (HarmonyOS PC)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/mysql/mysql-server"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mysql-client-8.4 supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # MySQL 8.4 requires C++20 (std::bit_floor/bit_ceil/popcount in
        # mysys). Manage the standard inside the recipe so the toolchain
        # does not append a conflicting -std flag after upstream's
        # CMAKE_CXX_STANDARD (profile cppstd=17 would win and break <bit>).
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "mysql-client-8.4 supports only OHOS armv8 targets"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "mysql-client-8.4/8.4.11 provides the static client library "
                "only; the shared libmysql target is skipped on OHOS "
                "(see notes.md)"
            )

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("zlib/1.3.1")
        self.requires("ncurses/6.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # R39: official CDN source (cdn.mysql.com is the primary release
        # channel for MySQL tarballs); GitHub tag archive as fallback.
        source = self.conan_data["sources"]
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # MySQL ships its own Find Modules for these libraries (cmake/ssl.cmake,
        # cmake/zlib.cmake, cmake/curses.cmake); do not let CMakeDeps inject
        # competing package configs (R26/R32/R33: system-name libraries are
        # resolved explicitly through cache variables instead).
        for dependency in ("openssl", "zlib", "ncurses"):
            self.dependencies[dependency].cpp_info.set_property(
                "cmake_find_mode", "none"
            )
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # OHOS is detected by CMake as an unknown system name; build as
            # Linux/aarch64 and gate OHOS specifics behind the OHOS variable
            # (same approach as mysql 8.0.46 and percona-server 8.4.10 ports).
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["OHOS"] = True
            # try_run() results for the OHOS cross toolchain (no target
            # emulator; the probes below are known-good on OHOS libc).
            # MySQL 8.4 configure.cmake runs three CHECK_C_SOURCE_RUNS
            # probes (setns / clock_gettime / clock_realtime); rapidjson
            # adds one CHECK_CXX_SOURCE_RUNS probe (std::regex support).
            tc.cache_variables["HAVE_SETNS_EXITCODE"] = 1
            tc.cache_variables["HAVE_CLOCK_GETTIME_EXITCODE"] = 0
            tc.cache_variables["HAVE_CLOCK_REALTIME_EXITCODE"] = 0
            tc.cache_variables["HAVE_RAPIDJSON_WITH_STD_REGEX_EXITCODE"] = 0
            tc.cache_variables["WITH_BUILD_ID"] = False

        openssl = self.dependencies["openssl"].cpp_info
        ncurses = self.dependencies["ncurses"].cpp_info
        zlib = self.dependencies["zlib"].cpp_info
        openssl_root = self.dependencies["openssl"].package_folder

        tc.cache_variables["WITH_SSL"] = "system"
        tc.cache_variables["OPENSSL_USE_STATIC_LIBS"] = True
        tc.cache_variables["OPENSSL_ROOT_DIR"] = openssl_root
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = openssl.includedirs[0]
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = os.path.join(
            openssl.libdirs[0], "libssl.a"
        )
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(
            openssl.libdirs[0], "libcrypto.a"
        )

        tc.cache_variables["WITH_ZLIB"] = "system"
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = zlib.includedirs[0]
        tc.cache_variables["ZLIB_LIBRARY"] = os.path.join(
            zlib.libdirs[0], "libz.a"
        )

        ncurses_libdir = ncurses.libdirs[0]
        tc.cache_variables["CURSES_NEED_WIDE"] = True
        tc.cache_variables["CURSES_INCLUDE_PATH"] = ncurses.includedirs[0]
        tc.cache_variables["CURSES_CURSES_H_PATH"] = ncurses.includedirs[0]
        tc.cache_variables["CURSES_LIBRARY"] = os.path.join(
            ncurses_libdir, "libncursesw.a"
        )
        tc.cache_variables["CURSES_FORM_LIBRARY"] = os.path.join(
            ncurses_libdir, "libformw.a"
        )
        tc.cache_variables["CURSES_NCURSES_LIBRARY"] = os.path.join(
            ncurses_libdir, "libncursesw.a"
        )

        tc.cache_variables["INSTALL_LAYOUT"] = "STANDALONE"
        tc.cache_variables["WITHOUT_SERVER"] = True
        tc.cache_variables["WITH_UNIT_TESTS"] = False
        tc.cache_variables["WITH_ROUTER"] = False
        tc.cache_variables["WITH_NDB"] = False
        tc.cache_variables["WITH_CURL"] = "none"
        tc.cache_variables["WITH_EDITLINE"] = "bundled"
        tc.cache_variables["WITH_ICU"] = "bundled"
        tc.cache_variables["WITH_LZ4"] = "bundled"
        tc.cache_variables["WITH_ZSTD"] = "bundled"
        tc.cache_variables["WITH_FIDO"] = "none"
        tc.cache_variables["WITH_KERBEROS"] = "none"
        tc.cache_variables["WITH_SYSTEMD"] = False
        tc.cache_variables["WITH_TCMALLOC"] = False
        tc.cache_variables["WITH_JEMALLOC"] = False
        tc.cache_variables["CMAKE_CXX_STANDARD"] = 20
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True

        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # OHOS build host: keep the parallel level low (make -j1 discipline
        # for large link steps on the HarmonyOS PC device).
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "docs"))
        rmdir(self, os.path.join(self.package_folder, "man"))
        self._validate_package()

    def _validate_package(self):
        root = Path(self.package_folder)
        required = [
            root / "include" / "mysql.h",
            root / "lib" / "libmysqlclient.a",
            root / "bin" / "mysql",
            root / "bin" / "mysqladmin",
            root / "bin" / "mysqldump",
            root / "bin" / "mysql_config",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ConanException(
                "required mysql client artifacts are missing: "
                + ", ".join(missing)
            )

        for forbidden in ("mysqld", "mysqlrouter"):
            if (root / "bin" / forbidden).exists():
                raise ConanException(
                    f"server/router executable unexpectedly installed: {forbidden}"
                )

    def package_info(self):
        self.cpp_info.libs = ["mysqlclient"]
        self.cpp_info.includedirs = ["include", "include/mysql"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = [
            "openssl::openssl",
            "zlib::zlib",
            "ncurses::ncurses",
        ]
        self.cpp_info.system_libs = ["dl", "pthread", "m"]
        if not self.options.shared:
            libcxx = str(self.settings.compiler.get_safe("libcxx"))
            if libcxx == "libc++":
                self.cpp_info.system_libs.extend(["c++", "c++abi", "unwind"])
            elif libcxx:
                self.cpp_info.system_libs.append("stdc++")
        self.cpp_info.set_property("cmake_file_name", "mysqlclient")
        self.cpp_info.set_property("cmake_target_name", "mysqlclient::mysqlclient")
        self.cpp_info.set_property("pkg_config_name", "mysqlclient")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
