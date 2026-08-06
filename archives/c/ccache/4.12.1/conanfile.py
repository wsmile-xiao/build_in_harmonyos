#!/usr/bin/env python3
"""Conan recipe — ccache 4.12.1

C/C++ compiler cache that speeds up recompilation by caching compilation
results. ccache uses CMake's FetchContent mechanism to manage its third-party
dependencies (blake3, fmt, hiredis, xxhash, zstd, etc.) at build time.

Most dependencies (blake3, cpphttplib, fmt, nonstd-span, tl-expected) are
bundled in the source tree. Three dependencies (hiredis, xxhash, zstd) are
downloaded via FetchContent. This recipe pre-downloads those three to work
around environments where GitHub is not directly reachable.

Build system: CMake
License: GPL-3.0-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


# FetchContent dependencies that ccache downloads at build time.
# Pre-downloaded by this recipe to avoid GitHub connectivity issues.
_FETCHCONTENT_DEPS = [
    {
        "name": "Hiredis",
        "urls": [
            "https://gh-proxy.com/https://github.com/redis/hiredis/archive/refs/tags/v1.3.0.tar.gz",
            "https://mirror.ghproxy.com/https://github.com/redis/hiredis/archive/refs/tags/v1.3.0.tar.gz",
            "https://github.com/redis/hiredis/archive/refs/tags/v1.3.0.tar.gz",
        ],
        "sha256": "25cee4500f359cf5cad3b51ed62059aadfc0939b05150c1f19c7e2829123631c",
        "subdir": "hiredis-1.3.0",
    },
    {
        "name": "Xxhash",
        "urls": [
            "https://gh-proxy.com/https://github.com/Cyan4973/xxhash/archive/refs/tags/v0.8.3.tar.gz",
            "https://mirror.ghproxy.com/https://github.com/Cyan4973/xxhash/archive/refs/tags/v0.8.3.tar.gz",
            "https://github.com/Cyan4973/xxhash/archive/refs/tags/v0.8.3.tar.gz",
        ],
        "sha256": "aae608dfe8213dfd05d909a57718ef82f30722c392344583d3f39050c7f29a80",
        "subdir": "xxHash-0.8.3",
    },
    {
        "name": "Zstd",
        "urls": [
            "https://gh-proxy.com/https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz",
            "https://mirror.ghproxy.com/https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz",
            "https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz",
        ],
        "sha256": "eb33e51f49a15e023950cd7825ca74a4a2b43db8354825ac24fc1b7ee09e6fa3",
        "subdir": "zstd-1.5.7",
    },
]


class CcacheConan(ConanFile):
    name = "ccache"
    version = "4.12.1"
    description = "A fast C/C++ compiler cache"
    license = "GPL-3.0-or-later"
    homepage = "https://ccache.dev/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # ccache uses FetchContent (DEPS=DOWNLOAD) to retrieve third-party
        # dependencies at build time. We pre-download the three external deps
        # (hiredis, xxhash, zstd) and point FetchContent to local directories.
        deps_dir = os.path.join(self.build_folder, "deps")
        for dep in _FETCHCONTENT_DEPS:
            dep_dir = os.path.join(deps_dir, dep["subdir"])
            var_name = f"FETCHCONTENT_SOURCE_DIR_{dep['name'].upper()}"
            tc.variables[var_name] = dep_dir
        # All storage backends enabled (no trimming)
        tc.variables["DEPS"] = "DOWNLOAD"
        tc.variables["REDIS_STORAGE_BACKEND"] = "ON"
        tc.variables["HTTP_STORAGE_BACKEND"] = "ON"
        # Disable testing in the package build; tests are in test_package
        tc.variables["ENABLE_TESTING"] = "OFF"
        tc.variables["ENABLE_IPO"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Pre-download FetchContent dependencies to local directories
        deps_dir = os.path.join(self.build_folder, "deps")
        for dep in _FETCHCONTENT_DEPS:
            dep_dir = os.path.join(deps_dir, dep["subdir"])
            if not os.path.isdir(dep_dir):
                get(self, url=dep["urls"], sha256=dep["sha256"],
                    destination=deps_dir, strip_root=False)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
