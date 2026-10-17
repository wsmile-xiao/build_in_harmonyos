#!/usr/bin/env python3
"""Conan recipe for GameNetworkingSockets 1.6.0 — Valve's game networking
library (reliable UDP transport, extracted from SteamNetworkingSockets).

HarmonyOS PC (aarch64-linux-ohos, musl libc) adaptation:
  - Crypto: upstream default USE_CRYPTO=OpenSSL, satisfied by the conan
    openssl/3.5.8.1 package (>= 1.1.1 required by upstream; EVP_MD_CTX_free
    symbol check passes).
  - protobuf: upstream wire protocol uses google protobuf. The registry's
    protobuf/33.6.1 exports protobuf-config.cmake with cmake_find_mode=none,
    so we point Protobuf_DIR/utf8_range_DIR/absl_DIR at the installed config
    files directly (mirrors the grpc/brpc recipes' wiring).
  - protoc: the registry protobuf package ships an OHOS-native protoc binary
    (host is also OHOS arm64 so it runs directly); its libc++_shared.so
    dependency needs the SDK's libc++ dir prepended to LD_LIBRARY_PATH in
    the build environment (see brpc recipe for the same treatment).
  - CMAKE_SYSTEM_NAME=Linux: upstream's set_target_common_gns_properties()
    only recognizes Linux/Darwin/FreeBSD/OpenBSD/Windows and FATAL_ERRORs
    otherwise. CMake maps OHOS to "HarmonyOS", which is not in that list.
    OHOS userspace is a Linux kernel + musl libc system — exactly what the
    LINUX define + epoll datagram path targets. Also the epoll backend is
    selected under the non-Apple/BSD `#else` branch of platform_sockets.h.
  - ENABLE_ICE=ON / USE_STEAMWEBRTC=OFF: upstream's default is ENABLE_ICE=ON,
    which only adds the STEAMNETWORKINGSOCKETS_ENABLE_ICE define and compiles
    the NATIVE ICE client (steamnetworkingsockets_ice_client.cpp, a pure POSIX
    RFC8489-subset implementation) — it needs NO submodule and builds clean
    on OHOS (verified locally with BUILD_TESTS=ON). We keep the default so the
    shipped library carries upstream's default P2P surface. USE_STEAMWEBRTC
    stays OFF: that is the option which would need the huge webrtc submodule
    (empty in the release tarball) and the abseil submodule pinned to
    lts_2020_02_25, which conflicts with protobuf 33.x's abseil 20260107.
  - CMAKE_POLICY_VERSION_MINIMUM=3.5 passed on the command line (upstream
    declares cmake_minimum_required 3.15).
  - musl notes: unlike its QUIC-family sibling msquic, GNS does NOT trip
    the two musl traps: (a) it never calls pthread_setaffinity_np; (b) the
    CMSG_NXTHDR loop in steamnetworkingsockets_socketthread.cpp sits
    inside `#if PlatformSupportsRecvMsg() && PlatformSupportsRecvTOS()`,
    and PlatformSupportsRecvTOS() falls back to false on OHOS (musl does
    not define IP_RECVTOS in the glibc-expected way), so the ancillary-
    data walker is compiled out. Zero source patches needed.

Key rules honored:
  - R8/R9: make -j1 (bounded parallelism).
  - R26: libGameNetworkingSockets_s.a / libGameNetworkingSockets.so do not
    clash with any system library name.
  - R32: settings.os check uses `in ("Linux", "OHOS")`.
  - R33: compiler executables come from Conan conf, never bare env CC.
  - R38: library package — no CLI executables built (BUILD_TOOLS=OFF,
    BUILD_EXAMPLES=OFF), no commands.json needed.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get


class GamenetworkingsocketsConan(ConanFile):
    name = "gamenetworkingsockets"
    version = "1.6.0"
    description = "Valve's reliable UDP transport library for games (GameNetworkingSockets)"
    license = "MIT"
    homepage = "https://github.com/ValveSoftware/GameNetworkingSockets"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    languages = "C", "C++"
    topics = ("networking", "udp", "game", "steam", "valve")

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
        # No patches: see module docstring (musl traps compiled out).
        pass

    def requirements(self):
        # Upstream requires OpenSSL >= 1.1.1 for EVP functionality.
        self.requires("openssl/3.5.8.1")
        # Wire protocol; registry package also provides the protoc binary.
        self.requires("protobuf/33.6.1")

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
                "gamenetworkingsockets supports OHOS armv8 only"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain_libcpp_dir(self):
        """SDK libc++_shared.so directory (for running the OHOS protoc)."""
        cc = ""
        conf = self.conf.get("tools.build:compiler_executables")
        if conf:
            cc = str(conf.get("cpp", ""))
        if not cc:
            return ""
        cc_real = os.path.realpath(cc)
        cand = os.path.join(
            os.path.dirname(os.path.dirname(cc_real)),
            "lib", "aarch64-linux-ohos", "c++",
        )
        return cand if os.path.isdir(cand) else ""

    def generate(self):
        CMakeDeps(self).generate()

        # The registry protobuf package ships an OHOS-target protoc; the
        # build machine is native OHOS arm64 so it runs directly, but its
        # libc++_shared.so must be findable (same wiring as brpc).
        env = Environment()
        libcpp = self._toolchain_libcpp_dir()
        if libcpp:
            env.prepend_path("LD_LIBRARY_PATH", libcpp)
        env.vars(self, scope="build").save_script("gns_protoc_libcpp_env")

        tc = CMakeToolchain(self)
        # Upstream only recognizes Linux/Darwin/FreeBSD/OpenBSD/Windows in
        # set_target_common_gns_properties(); CMake maps OHOS to HarmonyOS
        # which is not in that list (fatal). OHOS = Linux kernel + musl.
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # protobuf's registry package exports cmake_find_mode=none, so point
        # find_package(Protobuf CONFIG) at the installed config files
        # directly (mirrors grpc/brpc recipes).
        protobuf = self.dependencies["protobuf"]
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        abseil = self.dependencies["abseil-cpp"]
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")

        # find_package(OpenSSL) via the registry package root.
        openssl = self.dependencies["openssl"]
        tc.variables["OPENSSL_ROOT_DIR"] = openssl.package_folder.replace("\\", "/")
        # The registry openssl package ships its own OpenSSLConfig.cmake
        # (declaring OpenSSL::Crypto / OpenSSL::SSL, which upstream's
        # check_symbol_exists links against). CMakeDeps' generated
        # openssl-config.cmake only declares openssl::openssl and would win
        # the CONFIG search via CMAKE_PREFIX_PATH — point OpenSSL_DIR at the
        # package's native config explicitly.
        tc.variables["OpenSSL_DIR"] = os.path.join(
            openssl.package_folder.replace("\\", "/"), "lib", "cmake", "OpenSSL"
        )
        # Classic module variables too (harmless; some probes read them).
        openssl_pkg = openssl.package_folder.replace("\\", "/")
        tc.variables["OPENSSL_INCLUDE_DIR"] = os.path.join(openssl_pkg, "include")
        tc.variables["OPENSSL_INCLUDE_DIRS"] = os.path.join(openssl_pkg, "include")
        tc.variables["OPENSSL_SSL_LIBRARY"] = os.path.join(openssl_pkg, "lib", "libssl.a")
        tc.variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(openssl_pkg, "lib", "libcrypto.a")

        # Library-only shape.
        tc.variables["BUILD_SHARED_LIB"] = bool(self.options.shared)
        tc.variables["BUILD_STATIC_LIB"] = not bool(self.options.shared)
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_TESTS"] = False       # upstream tests run locally, see notes.md
        tc.variables["BUILD_TOOLS"] = False       # cert tool needs the vjson submodule (empty in tarball)
        tc.variables["ENABLE_ICE"] = True         # upstream default; native ICE client is pure POSIX, no submodule needed
        tc.variables["USE_STEAMWEBRTC"] = False   # webrtc submodule unavailable; abseil pin conflicts
        tc.variables["LTO"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM on the command line per environment rule
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Drop the cmake export dir: consumers come through conan's
        # generated find modules, and GameNetworkingSocketsConfig.cmake
        # hard-references protobuf targets that conan consumers wire
        # themselves (kept out per package hygiene).
        import shutil
        for sub in (os.path.join("lib", "cmake"),):
            full = os.path.join(self.package_folder, sub)
            if os.path.isdir(full):
                shutil.rmtree(full)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "GameNetworkingSockets")
        if self.options.shared:
            self.cpp_info.set_property("cmake_target_name", "GameNetworkingSockets::GameNetworkingSockets")
            self.cpp_info.libs = ["GameNetworkingSockets"]
        else:
            self.cpp_info.set_property("cmake_target_name", "GameNetworkingSockets::GameNetworkingSockets_s")
            self.cpp_info.libs = ["GameNetworkingSockets_s"]
            self.cpp_info.defines.append("STEAMNETWORKINGSOCKETS_STATIC_LINK")
        self.cpp_info.set_property("pkg_config_name", "GameNetworkingSockets")
        self.cpp_info.includedirs = [os.path.join("include", "GameNetworkingSockets")]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
        # NOTE: no cpp_info.requires entries. The registry protobuf package
        # exports cmake_find_mode=none, so CMakeDeps does not generate a
        # config for it — a `find_dependency(protobuf)` inside our generated
        # config would always fail for consumers (same reasoning as brpc).
        # Consumers wire Protobuf_DIR/utf8_range_DIR/absl_DIR themselves when
        # they need the protobuf CMake targets (see test_package).
