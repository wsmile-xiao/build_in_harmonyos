#!/usr/bin/env python3
"""Conan recipe for Transmission 4.1.3 utilities built with CMake."""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir


class TransmissionExtraConan(ConanFile):
    name = "transmission-extra"
    version = "4.1.3"
    description = "Transmission torrent create, edit, and show command-line utilities"
    license = "GPL-2.0-only OR GPL-3.0-only"
    homepage = "https://transmissionbt.com/"
    url = "https://github.com/transmission/transmission"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("curl/8.15.0")
        self.requires("openssl/3.5.6.1")
        self.requires("zlib/1.3.1.1")
        self.requires("libevent/2.1.13")
        self.requires("libdeflate/1.25")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"transmission-extra supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables.update({
            "ENABLE_DAEMON": False,
            "ENABLE_GTK": False,
            "ENABLE_QT": False,
            "ENABLE_MAC": False,
            "ENABLE_CLI": False,
            "ENABLE_UTILS": True,
            "ENABLE_TESTS": False,
            "ENABLE_UTP": True,
            "ENABLE_NLS": False,
            "INSTALL_WEB": False,
            "REBUILD_WEB": False,
            "INSTALL_DOC": False,
            "INSTALL_LIB": False,
            "RUN_CLANG_TIDY": False,
            "WITH_INOTIFY": False,
            "WITH_KQUEUE": False,
            "WITH_SYSTEMD": False,
            "WITH_CRYPTO": "openssl",
            "USE_SYSTEM_EVENT2": True,
            "USE_SYSTEM_DEFLATE": True,
            "USE_SYSTEM_DHT": False,
            "USE_SYSTEM_MINIUPNPC": False,
            "USE_SYSTEM_NATPMP": False,
            "USE_SYSTEM_UTP": False,
            "USE_SYSTEM_B64": False,
            "USE_SYSTEM_PSL": False,
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
        })
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG"] = "-Wl,-rpath,"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP"] = ":"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG"] = "-Wl,-rpath-link,"
            tc.cache_variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        bundled = {
            "psl": ("libpsl.bld", "psl-build", "libpsl.a"),
            "natpmp": ("libnatpmp.bld", "natpmp-build", "libnatpmp.a"),
            "miniupnpc": (
                os.path.join("miniupnp", "miniupnpc.bld"),
                "miniupnpc-build",
                "libminiupnpc.a",
            ),
            "dht": ("dht.bld", "dht-build", "libdht.a"),
        }
        for target, (folder, build_dir, library) in bundled.items():
            cmake.build(target=target)
            source = os.path.join(
                self.build_folder, "third-party", folder, "src", build_dir
            )
            prefix = os.path.join(
                self.build_folder, "third-party", folder, "pfx"
            )
            copy(self, library, source, os.path.join(prefix, "lib"))
            if target == "psl":
                copy(self, "libpsl.h", source, os.path.join(prefix, "include"))
        cmake.build()

    def package(self):
        CMake(self).install()
        bindir = os.path.join(self.package_folder, "bin")
        for pattern in (
            "transmission-remote*",
            "natpmpc",
            "upnpc*",
            "upnp-listdevices*",
            "external-ip.sh",
        ):
            rm(self, pattern, bindir)
        for directory in ("include", "lib", "share"):
            rmdir(self, os.path.join(self.package_folder, directory))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_binaries()

    def _sign_binaries(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        for binary in glob.glob(os.path.join(self.package_folder, "bin", "transmission-*")):
            if not os.path.isfile(binary):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{binary}"')
            self.run(f'"{signer}" sign -inFile "{binary}" -outFile "{binary}" -selfSign 1')

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
