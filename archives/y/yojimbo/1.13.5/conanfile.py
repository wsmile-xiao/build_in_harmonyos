#!/usr/bin/env python3
"""Conan recipe for yojimbo 1.13.5 — networkprotocol's secure client/server
UDP protocol library for games (built on netcode.io + reliable.io +
libsodium, all vendored in-tree).

HarmonyOS PC (aarch64-linux-ohos, musl libc) adaptation:
  - Zero external Conan dependencies: upstream vendors everything. The
    default (non-YOJIMBO_SYSTEM_*) build compiles sodium/sodium.c,
    netcode/netcode.c, reliable/reliable.c and tlsf/tlsf.c as OBJECT
    libraries folded into the single libyojimbo archive; serialize is
    header-only. The recipe keeps that self-contained shape — no
    libsodium/netcode/reliable requires, so there is no registry link to
    break and consumers link one archive.
  - Platform gates: netcode.h / reliable.h / yojimbo_config.h select
    *_PLATFORM_UNIX for anything that is not _WIN32/__APPLE__, and pick
    little-endian via __aarch64__ / __LITTLE_ENDIAN__ — OHOS takes the
    plain POSIX (BSD sockets, fcntl O_NONBLOCK, gettimeofday) path with
    no patching.
  - QUIC-family musl pre-scan (msquic 2.6.1 / GameNetworkingSockets 1.6.0
    template): (a) zero pthread_setaffinity_np calls anywhere in tree;
    (b) zero CMSG_NXTHDR ancillary-data walkers — neither musl trap can
    hit this codebase.
  - CMAKE_SYSTEM_NAME stays whatever Conan's OHOS toolchain maps it to
    (HarmonyOS): upstream's CMakeLists has no platform table / FATAL_ERROR
    on unknown systems (unlike GameNetworkingSockets), so no Linux
    override is needed.
  - YOJIMBO_BUILD_TESTS=OFF for the shipped library (tests are built and
    run locally from the full source; see notes.md and reports/).
  - YOJIMBO_INSTALL=ON installs the library plus its own headers and the
    vendored public headers (sodium.h / netcode.h / reliable.h /
    serialize.h / tlsf.h) that yojimbo.h transitively needs.

Key rules honored:
  - R8/R9: make -j1 (bounded parallelism).
  - R26: libyojimbo.a / libyojimbo.so do not clash with any system library.
  - R32: settings.os check uses `in ("Linux", "OHOS")`.
  - R33: compiler executables come from the Conan toolchain, never bare env.
  - R38: library package — no CLI executables installed, no commands.json.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class YojimboConan(ConanFile):
    name = "yojimbo"
    version = "1.13.5"
    description = "A network library for games with client/server UDP encryption (netcode.io + reliable.io based)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/networkprotocol/yojimbo"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    languages = "C", "C++"
    topics = ("networking", "udp", "game", "client-server", "crypto")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        # No patches: the whole tree is musl/POSIX clean (see docstring).
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        # R32: accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "yojimbo supports OHOS armv8 only"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Library-only shape: the test/example/soak executables are built
        # and run locally from the source tree (see notes.md); the shipped
        # package installs only the library and headers.
        tc.variables["YOJIMBO_BUILD_TESTS"] = False
        tc.variables["YOJIMBO_INSTALL"] = True
        # Keep the vendored (self-contained) build: system sodium/netcode/
        # reliable/tlsf are NOT registry packages.
        tc.variables["YOJIMBO_SYSTEM_SODIUM"] = False
        tc.variables["YOJIMBO_SYSTEM_DEPS"] = False
        tc.variables["YOJIMBO_SYSTEM_TLSF"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # R8/R9: bounded parallelism on the shared CI workers.
        cmake.build(cli_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENCE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Yojimbo")
        self.cpp_info.set_property("cmake_target_name", "Yojimbo::yojimbo")
        self.cpp_info.libs = ["yojimbo"]
        if self.settings.os in ("Linux", "OHOS"):
            # ceil/floor in the reliable-ordered channel (upstream links m
            # on every non-Windows platform).
            self.cpp_info.system_libs = ["m"]
