#!/usr/bin/env python3
"""Conan recipe for Percona Server 8.4.10-10 client library/tools."""

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


class PerconaServerConan(ConanFile):
    name = "percona-server"
    version = "8.4.10-10"
    description = "Percona Server for MySQL client library and client tools"
    license = "GPL-2.0-only"
    homepage = "https://github.com/percona/percona-server"
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
                f"percona-server supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "percona-server supports only OHOS armv8 targets"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "percona-server currently provides only the static client library"
            )

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("ncurses/6.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        for dependency in ("openssl", "ncurses"):
            self.dependencies[dependency].cpp_info.set_property(
                "cmake_find_mode", "none"
            )
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["OHOS"] = True
            tc.cache_variables["protobuf_BUILD_SHARED_LIBS"] = False
            tc.cache_variables["absl_BUILD_SHARED_LIBS"] = False
            tc.cache_variables["HAVE_SETNS_EXITCODE"] = 1
            tc.cache_variables["HAVE_CLOCK_GETTIME_EXITCODE"] = 0
            tc.cache_variables["HAVE_CLOCK_REALTIME_EXITCODE"] = 0
            tc.cache_variables["WITH_BUILD_ID"] = False

        openssl = self.dependencies["openssl"].cpp_info
        ncurses = self.dependencies["ncurses"].cpp_info
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

        shared = bool(self.options.shared)
        tc.cache_variables["BUILD_SHARED_LIBS"] = shared
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = shared or bool(
            self.options.get_safe("fPIC", True)
        )
        tc.cache_variables["INSTALL_LAYOUT"] = "STANDALONE"
        tc.cache_variables["WITHOUT_SERVER"] = True
        tc.cache_variables["WITH_UNIT_TESTS"] = False
        tc.cache_variables["WITH_ROUTER"] = False
        tc.cache_variables["WITH_NDB"] = False
        tc.cache_variables["WITH_PAM"] = False
        tc.cache_variables["WITH_AUTHENTICATION_LDAP"] = False
        tc.cache_variables["WITH_AUTHENTICATION_KERBEROS"] = False
        tc.cache_variables["WITH_AUTHENTICATION_WEBAUTHN"] = False
        tc.cache_variables["WITH_AUTHENTICATION_CLIENT_PLUGINS"] = False
        tc.cache_variables["WITH_PERCONA_AUTHENTICATION_LDAP"] = False
        tc.cache_variables["WITH_FIDO"] = "none"
        tc.cache_variables["WITH_KERBEROS"] = "none"
        tc.cache_variables["WITH_EDITLINE"] = "bundled"
        tc.cache_variables["WITH_ZLIB"] = "bundled"
        tc.cache_variables["WITH_LZ4"] = "bundled"
        tc.cache_variables["WITH_ZSTD"] = "bundled"
        tc.cache_variables["WITH_ICU"] = "bundled"
        tc.cache_variables["WITH_PROTOBUF"] = "bundled"
        tc.cache_variables["WITH_CURL"] = "bundled"
        tc.cache_variables["WITH_SYSTEMD"] = False
        tc.cache_variables["WITH_COREDUMPER"] = False
        tc.cache_variables["WITH_COMPONENT_KEYRING_KMIP"] = False
        tc.cache_variables["WITHOUT_COMPONENT_KEYRING_KMIP"] = True
        tc.cache_variables["WITH_TCMALLOC"] = False
        tc.cache_variables["WITH_JEMALLOC"] = False
        tc.cache_variables["ENABLED_PROFILING"] = False
        tc.cache_variables["ENABLED_LOCAL_INFILE"] = False
        tc.cache_variables["WITH_CLIENT_PROTOCOL_TRACING"] = False
        tc.cache_variables["WITH_TEST_TRACE_PLUGIN"] = False
        tc.cache_variables["CMAKE_SKIP_INSTALL_ALL_DEPENDENCY"] = False

        if shared:
            origin = "$ORIGIN"
            if str(self.settings_build.os) != "Windows":
                origin = r"\$ORIGIN"
            tc.cache_variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
            tc.cache_variables["CMAKE_INSTALL_RPATH"] = f"{origin}/../lib;{origin}"
            tc.cache_variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = False

        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
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
            root / "lib",
            root / "bin" / "mysql",
            root / "bin" / "mysql_config",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ConanException(
                "required Percona client artifacts are missing: "
                + ", ".join(missing)
            )

        library_names = {
            path.name for path in (root / "lib").glob("libperconaserverclient*")
        }
        if not library_names:
            raise ConanException("libperconaserverclient was not installed")

        for forbidden in ("mysqld", "mysqlrouter"):
            if (root / "bin" / forbidden).exists():
                raise ConanException(
                    f"server/router executable unexpectedly installed: {forbidden}"
                )

    def package_info(self):
        self.cpp_info.libs = ["perconaserverclient"]
        self.cpp_info.includedirs = ["include", "include/mysql"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["openssl::openssl", "ncurses::ncurses"]
        self.cpp_info.system_libs = ["dl", "pthread", "rt", "resolv", "m"]
        if not self.options.shared:
            libcxx = str(self.settings.compiler.get_safe("libcxx"))
            if libcxx == "libc++":
                self.cpp_info.system_libs.extend(["c++", "c++abi", "unwind"])
            elif libcxx:
                self.cpp_info.system_libs.append("stdc++")
        self.cpp_info.set_property("cmake_file_name", "percona-server")
        self.cpp_info.set_property(
            "cmake_target_name", "percona-server::percona-server"
        )
        self.cpp_info.set_property("pkg_config_name", "percona-server")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
