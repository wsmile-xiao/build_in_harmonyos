#!/usr/bin/env python3
"""Conan recipe for LibreSSL 3.9.1."""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
    save,
)
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version


class LibreSSLConan(ConanFile):
    name = "libressl"
    version = "3.9.1"
    description = "TLS and cryptography stack forked from OpenSSL by OpenBSD"
    license = ("OpenSSL", "BSD-3-Clause", "ISC")
    homepage = "https://www.libressl.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("ssl", "tls", "cryptography")
    package_type = "library"
    provides = "openssl"

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
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if self.options.shared and is_msvc(self) and is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration(
                "LibreSSL shared libraries cannot use the static MSVC runtime"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        platform_modules = os.path.join(self.build_folder, "_cmake_modules")
        save(
            self,
            os.path.join(platform_modules, "Platform", "HarmonyOS.cmake"),
            "include(Platform/Linux)\n",
        )
        save(
            self,
            os.path.join(platform_modules, "Platform", "OHOS.cmake"),
            "include(Platform/Linux)\n",
        )

        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            ohos_processor = {
                "armv8": "aarch64",
                "armv7": "arm",
                "x86_64": "x86_64",
                "x86": "x86",
            }.get(str(self.settings.arch), str(self.settings.arch))
            tc.variables["CMAKE_MODULE_PATH"] = platform_modules
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = ohos_processor
            tc.variables["LIBRESSL_TARGET_PROCESSOR"] = ohos_processor
            tc.variables["OHOS_ARCH"] = {
                "armv8": "arm64-v8a",
                "armv7": "armeabi-v7a",
                "x86_64": "x86_64",
                "x86": "x86",
            }.get(str(self.settings.arch), ohos_processor)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe(
            "fPIC", True
        )
        tc.variables["LIBRESSL_SKIP_INSTALL"] = False
        tc.variables["LIBRESSL_APPS"] = True
        tc.variables["LIBRESSL_TESTS"] = True
        tc.variables["ENABLE_EXTRATESTS"] = True
        tc.variables["ENABLE_NC"] = False
        tc.variables["ENABLE_ASM"] = True
        tc.variables["OPENSSLDIR"] = "res"
        if is_msvc(self):
            tc.preprocessor_definitions["_CRT_SUPPRESS_RESTRICT"] = 1
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            cmake.ctest(
                cli_args=[
                    "--output-on-failure",
                    "--no-tests=error",
                    "--parallel",
                    "2",
                ]
            )
        else:
            self.output.info(
                "Cross build: upstream CTest executables compiled but cannot "
                "run on the build host."
            )

    def package(self):
        copy(
            self,
            "*COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        CMake(self).install()
        bindir = os.path.join(self.package_folder, "bin")
        if self.settings.os == "Windows" and self.options.shared:
            for app in ("openssl.exe", "ocspcheck.exe", "nc.exe"):
                rm(self, app, bindir)
        else:
            rmdir(self, bindir)
        rm(self, "*.cmake", os.path.join(self.package_folder, "include"))
        rmdir(self, os.path.join(self.package_folder, "include", "CMakeFiles"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "LibreSSL")
        self.cpp_info.set_property("pkg_config_name", "openssl")

        crypto = self.cpp_info.components["crypto"]
        crypto.set_property("cmake_target_name", "LibreSSL::Crypto")
        crypto.set_property("pkg_config_name", "libcrypto")
        crypto.libs = [self._lib_name("crypto")]
        crypto.resdirs = ["res"]
        if self.settings.os in ("Linux", "FreeBSD"):
            crypto.system_libs = ["pthread", "rt"]
        elif str(self.settings.os) == "OHOS":
            crypto.system_libs = ["pthread"]
        elif self.settings.os == "SunOS":
            crypto.system_libs = ["nsl", "socket"]
        elif self.settings.os == "Windows":
            crypto.system_libs = ["ws2_32", "bcrypt"]

        ssl = self.cpp_info.components["ssl"]
        ssl.set_property("cmake_target_name", "LibreSSL::SSL")
        ssl.set_property("pkg_config_name", "libssl")
        ssl.libs = [self._lib_name("ssl")]
        ssl.resdirs = ["res"]
        ssl.requires = ["crypto"]

        tls = self.cpp_info.components["tls"]
        tls.set_property("cmake_target_name", "LibreSSL::TLS")
        tls.set_property("pkg_config_name", "libtls")
        tls.libs = [self._lib_name("tls")]
        tls.resdirs = ["res"]
        tls.requires = ["ssl", "crypto"]

    def _lib_name(self, name):
        if self.settings.os == "Windows" and (
            Version(self.version) >= "3.1.0" or self.options.shared
        ):
            matches = glob.glob(
                os.path.join(self.package_folder, "lib", f"*{name}*")
            )
            if not matches:
                raise ConanInvalidConfiguration(
                    f"Unable to locate packaged LibreSSL library: {name}"
                )
            return os.path.basename(matches[0]).split(".")[0].replace("lib", "")
        return name
