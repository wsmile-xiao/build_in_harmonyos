#!/usr/bin/env python3
"""Conan recipe — tdlib 1.8.0 (CMake).

TDLib (Telegram Database library) is the cross-platform client library for
Telegram, written in C++14. Upstream builds with CMake and requires OpenSSL
and zlib; both are mandatory — the top-level CMakeLists aborts configuration
with "Can't find OpenSSL/zlib: stop TDLib building" when either is missing.

Artifacts: `libtdjson.so` (JSON/C client API `td_json_client.h`),
`libtdjson_static.a`, `libtdclient.a`, `libtdcore.a`, `libtdapi.a`,
`libtdutils.a`, `libtdactor.a`, `libtdnet.a`, `libtdsqlite.a`, `libtddb.a`,
plus the upstream `Td` CMake package (`Td::TdJson`, `Td::TdJsonStatic`,
`Td::TdStatic`) and pkg-config files.

OHOS notes (all build-configuration level — no upstream source is patched)
--------------------------------------------------------------------------
1. CMake >= 4.0 removed compatibility with `cmake_minimum_required(<3.5)`;
   tdlib 1.8.0 asks for 3.0.2 and the OHOS host ships CMake 4.1.2. The policy
   floor is passed on the configure command line. It cannot go into the Conan
   toolchain file: CMake loads the toolchain only at the first `project()`
   call, while `cmake_minimum_required` (CMakeLists.txt:1) is evaluated
   earlier — a toolchain-level `CMAKE_POLICY_VERSION_MINIMUM` is applied too
   late.
2. The Conan profile pins `compiler.cppstd=17`. tdlib appends `-std=c++14`
   itself (CMake/TdSetUpCompiler.cmake) but CMake places the standard flag of
   CMAKE_CXX_STANDARD *after* the project flags, so the compilation unit ends
   up as C++17. The MIME tables emitted by gperf at build time still contain
   `register` (removed in C++17), which clang rejects as an error under
   `-Wregister` (upstream only suppresses the C++14-era `-Wdeprecated-register`
   spelling). `-Wno-register` is appended through the Conan toolchain flags,
   so the generated tables compile without touching them.
3. tdlib consumes OpenSSL through the classic FindOpenSSL variable names
   (`OPENSSL_FOUND`, `OPENSSL_INCLUDE_DIR`, `OPENSSL_CRYPTO_LIBRARY`,
   `OPENSSL_SSL_LIBRARY`). Conan's CMakeDeps only defines the lowercase
   `openssl_*` variables, and the OHOS profile enables config mode
   (`CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`), so `find_package(OpenSSL)` would
   succeed without ever setting the uppercase names. The recipe wires the
   classic names to the Conan package (ohpcd ships static `libcrypto.a` /
   `libssl.a`), which also keeps OpenSSL linked statically into `libtdjson.so`
   (no `libssl.so`/`libcrypto.so` runtime dependency). zlib needs no such
   wiring: its Conan package generates `ZLIBConfig.cmake`, which already
   defines `ZLIB_FOUND` / `ZLIB_INCLUDE_DIR` / `ZLIB_LIBRARIES`.
4. The OHOS/aarch64 host *is* the target: the OHOS Conan profile does not set
   CMAKE_SYSTEM_NAME, so CMAKE_CROSSCOMPILING is FALSE and upstream's
   `test/`, `benchmark/` and `tg_cli` targets are built (and, for the tests,
   executed natively) exactly as upstream intends.
5. CMake has no platform module for HarmonyOS, so it never defines
   CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG: `libtdjson.so` ended up without a
   DT_SONAME and the installed `TdTargets.cmake` was stamped with
   IMPORTED_NO_SONAME (L5 quality gate). The flag is restored through CMake's
   CMAKE_USER_MAKE_RULES_OVERRIDE_<LANG> hook.

Upstream tests are executed for real on OHOS — see notes.md for the full
per-case ledger (208/208 cases of `run_all_tests`, the binary registered with
`add_test()` in test/CMakeLists.txt).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save


class TdlibConan(ConanFile):
    name = "tdlib"
    version = "1.8.0"
    description = (
        "TDLib — cross-platform client library for Telegram (C++14, JSON/C "
        "API). Builds libtdjson.so, the static tdclient/tdcore toolchain and "
        "the upstream Td CMake package."
    )
    license = "BSL-1.0"
    homepage = "https://github.com/tdlib/td"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("telegram", "tdlib", "client", "json", "cmake")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # Upstream default: tdclient/tdcore/... are static, while tdjson is always
    # declared SHARED by upstream, so the default package keeps both forms.
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The ohpcd openssl recipe revision is pinned: the conancenter recipe
        # rejects the OHOS/armv8/clang configuration, and without a pin Conan
        # resolves conancenter first and fails with "Invalid configuration:
        # Unsupported configuration (OHOS/armv8/clang)".
        self.requires("openssl/3.5.6#748fc4deb56588d6f8ce900b21e8eb0a")
        self.requires("zlib/1.3.2")

    def validate(self):
        # R32: accept both Linux and OHOS platform settings.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tdlib is only adapted for Linux/OHOS, not %s" % self.settings.os)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.extra_cxxflags.append("-Wno-register")
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"

        if self.settings.os == "OHOS":
            # CMake ships no platform module for HarmonyOS ("System is unknown
            # to cmake, create Platform/HarmonyOS"), so
            # CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG stays empty: libtdjson.so
            # gets no DT_SONAME and the installed TdTargets.cmake is stamped
            # with IMPORTED_NO_SONAME (downstream must link by full path).
            # The documented override hook restores the flag after the platform
            # rules have been read (same wiring as the cpr recipe).
            self._write_ohos_shared_lib_rules(tc)

            # Classic FindOpenSSL variable names (see module docstring #3).
            openssl = self.dependencies["openssl"]
            openssl_pkg = openssl.package_folder.replace("\\", "/")
            tc.cache_variables["OPENSSL_FOUND"] = True
            tc.cache_variables["OPENSSL_ROOT_DIR"] = openssl_pkg
            tc.cache_variables["OPENSSL_INCLUDE_DIR"] = "%s/include" % openssl_pkg
            tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = "%s/lib/libcrypto.a" % openssl_pkg
            tc.cache_variables["OPENSSL_SSL_LIBRARY"] = "%s/lib/libssl.a" % openssl_pkg
            tc.cache_variables["OPENSSL_LIBRARIES"] = "%s/lib/libssl.a;%s/lib/libcrypto.a" % (
                openssl_pkg, openssl_pkg)
            tc.cache_variables["OPENSSL_USE_STATIC_LIBS"] = True
        tc.generate()

    def _write_ohos_shared_lib_rules(self, tc):
        """Give OHOS the ELF shared-library link rule CMake normally reads from
        its platform modules (HarmonyOS has none)."""
        for lang in ("C", "CXX"):
            rules = os.path.join(
                self.generators_folder, "ohos-shared-lib-rules-%s.cmake" % lang.lower())
            save(self, rules, 'set(CMAKE_SHARED_LIBRARY_SONAME_%s_FLAG "-Wl,-soname,")\n' % lang)
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_%s" % lang] = rules

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # OHOS ships CMake 4.x, which refuses cmake_minimum_required(<3.5).
        # Must reach CMake before CMakeLists.txt:1 is parsed, hence cli_args
        # rather than a toolchain variable (see module docstring #1).
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def package(self):
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The package also ships the upstream "Td" CMake package
        # (lib/cmake/Td/TdConfig.cmake -> Td::TdJson / Td::TdJsonStatic /
        # Td::TdStatic) and pkg-config files; only the plain Conan metadata is
        # declared here so that the two naming schemes cannot collide.
        self.cpp_info.libs = ["tdjson"]
        self.cpp_info.set_property("pkg_config_name", "tdjson")
