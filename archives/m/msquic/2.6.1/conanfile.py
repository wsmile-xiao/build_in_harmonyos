#!/usr/bin/env python3
"""Conan recipe for msquic 2.6.1 — Microsoft's implementation of the
IETF QUIC protocol (pure C, CMake build system).

HarmonyOS PC (aarch64-linux-ohos, musl libc) adaptation:
  - QUIC_TLS_LIB=openssl: uses the conan-provided openssl/3.5.8.1 (>= 3.5.0
    required by upstream) instead of building the openssl submodule
    (submodules are not shipped in the release tarball).
  - QUIC_USE_EXTERNAL_OPENSSL + QUIC_OPENSSL_ROOT_DIR point CMake's
    FindOpenSSL at the conan package folder.
  - QUIC_BUILD_TOOLS/TEST/PERF=OFF, QUIC_ENABLE_LOGGING=OFF (lttng not
    available on OHOS; stub logging keeps the public ABI identical).
  - CMAKE_POLICY_VERSION_MINIMUM=3.5 passed on the command line (upstream
    declares cmake_minimum_required 3.16/3.20).
  - msquic's CMakeLists sets CMAKE_SYSTEM_NAME-derived CX_PLATFORM=linux,
    which matches OHOS's Linux kernel + musl userspace.

Patches (see patches/):
  - 0001: musl has no pthread_setaffinity_np (glibc extension); skip the
    post-create affinitization block on __OHOS__, mirroring upstream's
    own __ANDROID__ strategy (affinity = perf optimization only).
  - 0002/0003: musl's CMSG_NXTHDR macro mixes signed/unsigned operands;
    with the project's -Werror -Wsign-compare this fires inside the macro
    expansion on OHOS. Silence per translation unit via pragma.

Key rules honored:
  - R9:  make -j1 (bounded parallelism).
  - R26: libmsquic.so does not clash with any system library name.
  - R32: settings.os check uses `in ("Linux", "OHOS")`.
  - R33: compiler executables come from Conan conf, never bare env CC.
  - R38: library package — no commands.json needed (no CLI executables
    built with QUIC_BUILD_TOOLS=OFF).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir


class MsquicConan(ConanFile):
    name = "msquic"
    version = "2.6.1"
    description = "Cross-platform QUIC protocol implementation (Microsoft)"
    license = "MIT"
    homepage = "https://github.com/microsoft/msquic"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    languages = "C"
    topics = ("quic", "network", "protocol", "tls")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream requires OpenSSL >= 3.5.0 for the 'openssl' TLS provider
        # (QUIC API surface needs the 3.5+ TLS API set).
        self.requires("openssl/3.5.8.1")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # R32: accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # msquic's platform probe only understands WIN32 / APPLE / UNIX.
        # On an OHOS build host CMake auto-detects CMAKE_SYSTEM_NAME=HarmonyOS,
        # which sets none of those (CMake treats HarmonyOS as its own platform
        # class, not a UNIX variant) leaving CX_PLATFORM empty — the build then
        # compiles kqueue (BSD) and darwin sources and fails. OHOS userspace
        # is a Linux kernel + musl libc system, exactly what msquic's "linux"
        # platform targets (epoll/UDP datapath). Force it explicitly.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # CMAKE_SYSTEM_PROCESSOR: the OHOS-adapted toolchain does not set it
        # (host is HarmonyOS), leaving msquic's
        # `string(TOLOWER ${CMAKE_SYSTEM_PROCESSOR} SYSTEM_PROCESSOR)` with an
        # empty argument ("string no output variable specified" fatal error).
        # Set the target architecture explicitly.
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # msquic-specific options
        tc.variables["QUIC_BUILD_TOOLS"] = False      # no CLI tools (library only)
        tc.variables["QUIC_BUILD_TEST"] = False       # tests need googletest submodule + network
        tc.variables["QUIC_BUILD_PERF"] = False       # perf harness needs network
        tc.variables["QUIC_TLS_LIB"] = "openssl"      # conan-provided openssl 3.5.8
        tc.variables["QUIC_USE_EXTERNAL_OPENSSL"] = True
        tc.variables["QUIC_ENABLE_LOGGING"] = False   # lttng unavailable on OHOS; stub logging
        tc.variables["QUIC_STATIC_LINK_CRT"] = False
        tc.variables["QUIC_EMBED_GIT_HASH"] = False   # tarball is not a git repo
        tc.variables["QUIC_SOURCE_LINK"] = False
        tc.generate()

        # Point msquic's FindOpenSSL at the conan openssl package.
        openssl = self.dependencies["openssl"]
        tc_cmake = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        with open(tc_cmake, "a") as f:
            f.write(f"\nset(QUIC_OPENSSL_ROOT_DIR \"{openssl.package_folder}\")\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM on the command line per environment rule
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build(target="msquic")

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Drop cmake export dir not needed by consumers via conan (L0-style
        # cleanliness: keep include/ + lib/ only).
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "msquic")
        # msquic's own exported target is msquic::msquic
        self.cpp_info.set_property("cmake_target_name", "msquic::msquic")
        self.cpp_info.set_property("pkg_config_name", "msquic")
        self.cpp_info.libs = ["msquic"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
