#!/usr/bin/env python3
"""Conan recipe for curl 8.15.0 and libcurl."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    get,
    rmdir,
    save,
    unzip,
)


class CurlConan(ConanFile):
    name = "curl"  # conan_data-managed recipe, not external curl command
    version = "8.15.0.1"
    description = "Command-line URL transfer tool and client-side URL library"
    license = "curl"  # curl license, not external curl
    homepage = "https://curl.se/"
    url = "https://github.com/curl/curl"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"curl supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 3.5.6 references __fd_chk from libcrypto on OHOS. The 3.5.6.1
        # dependency recipe carries the narrow FD_SET portability fix.
        self.requires("openssl/3.5.6.1")
        # zlib/1.3.1.1 is the PIC static package required by shared consumers.
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        staged = os.path.join(
            os.path.expanduser("~"), "Download", source["filename"]
        )
        if os.path.isfile(staged):
            check_sha256(self, staged, source["sha256"])
            unzip(self, staged, destination=self.source_folder, strip_root=True)
        else:
            get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # curl 8.15 flattens dependency target LOCATION values when generating
        # libcurl.pc. Conan interface targets have no LOCATION, so use CMake's
        # native Find modules while retaining Conan's dependency search paths.
        for dependency in ("openssl", "zlib"):
            self.dependencies[dependency].cpp_info.set_property(
                "cmake_find_mode", "none"
            )
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            rules = os.path.join(
                self.generators_folder, "ohos-cmake-rules.cmake"
            )
            save(
                self,
                rules,
                "\n".join(
                    (
                        'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                        "set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "
                        '"-Wl,-rpath-link,")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                    )
                )
                + "\n",
            )
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules

        openssl = self.dependencies["openssl"].cpp_info
        zlib = self.dependencies["zlib"].cpp_info
        tc.cache_variables["OPENSSL_ROOT_DIR"] = self.dependencies[
            "openssl"
        ].package_folder
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = openssl.includedirs[0]
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = os.path.join(
            openssl.libdirs[0], "libssl.a"
        )
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(
            openssl.libdirs[0], "libcrypto.a"
        )
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = zlib.includedirs[0]
        tc.cache_variables["ZLIB_LIBRARY"] = os.path.join(
            zlib.libdirs[0], "libz.a"
        )

        shared = bool(self.options.shared)
        tc.cache_variables["BUILD_SHARED_LIBS"] = shared
        tc.cache_variables["BUILD_STATIC_LIBS"] = not shared
        tc.cache_variables["BUILD_STATIC_CURL"] = not shared
        tc.cache_variables["BUILD_CURL_EXE"] = True
        tc.cache_variables["BUILD_TESTING"] = True
        tc.cache_variables["BUILD_EXAMPLES"] = False
        # HMDFS denies the symlinks used by curl's versioned SOVERSION layout.
        # The OHOS rules above still emit an unversioned, relocatable SONAME.
        tc.cache_variables["CURL_LIBCURL_SOVERSION"] = False
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = shared or bool(
            self.options.get_safe("fPIC", True)
        )

        tc.cache_variables["CURL_USE_PKGCONFIG"] = False
        tc.cache_variables["CURL_USE_OPENSSL"] = True
        tc.cache_variables["OPENSSL_USE_STATIC_LIBS"] = True
        tc.cache_variables["CURL_ZLIB"] = "ON"

        # Keep the dependency surface reproducible and limited to Conan inputs.
        tc.cache_variables["ENABLE_ARES"] = False
        tc.cache_variables["CURL_BROTLI"] = "OFF"
        tc.cache_variables["CURL_ZSTD"] = "OFF"
        tc.cache_variables["USE_NGHTTP2"] = False
        tc.cache_variables["USE_LIBIDN2"] = False
        tc.cache_variables["CURL_USE_LIBPSL"] = False
        tc.cache_variables["CURL_USE_LIBSSH2"] = False
        tc.cache_variables["CURL_USE_LIBSSH"] = False
        tc.cache_variables["CURL_USE_GSASL"] = False
        tc.cache_variables["CURL_USE_GSSAPI"] = False
        tc.cache_variables["USE_LIBRTMP"] = False
        tc.cache_variables["CURL_DISABLE_LDAP"] = True
        tc.cache_variables["CURL_DISABLE_LDAPS"] = True
        tc.cache_variables["USE_NGTCP2"] = False
        tc.cache_variables["USE_NGHTTP3"] = False
        tc.cache_variables["USE_QUICHE"] = False
        tc.cache_variables["USE_MSH3"] = False
        tc.cache_variables["USE_OPENSSL_QUIC"] = False

        # OHOS headers expose the TCP API through netinet/tcp.h. Avoid the
        # conflicting Linux UAPI header without carrying a source patch.
        tc.cache_variables["HAVE_LINUX_TCP_H"] = False

        if shared:
            tc.cache_variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
            tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = False
            origin = "$ORIGIN"
            if str(self.settings_build.os) != "Windows":
                # Conan invokes CMake through a target-side shell on OHOS.
                # Protect $ORIGIN until CMake writes the linker/install rules.
                origin = r"\$ORIGIN"
            tc.cache_variables["CMAKE_INSTALL_RPATH"] = (
                f"{origin}/../lib;{origin}"
            )
            tc.cache_variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.build(target="testdeps")

        if not can_run(self):
            self.output.info(
                "cross-building: curl testdeps compiled but target tests cannot run"
            )
            return
        # runner.pm cleardir(log) cannot create the directory on HMDFS
        # when it does not already exist, causing all test servers to
        # fail opening their log files and cascade-fail dependent tests.
        os.makedirs(
            os.path.join(self.build_folder, "tests", "log"), exist_ok=True
        )
        self.run(
            f'perl "{os.path.join(self.source_folder, "tests", "runtests.pl")}" -a',
            cwd=os.path.join(self.build_folder, "tests"),
        )

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        CMake(self).install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["curl"]  # lib name, not external curl
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "CURL")
        self.cpp_info.set_property("cmake_target_name", "CURL::libcurl")
        self.cpp_info.set_property("pkg_config_name", "libcurl")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        if not self.options.shared:
            self.cpp_info.defines.append("CURL_STATICLIB")
