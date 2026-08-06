#!/usr/bin/env python3
"""Conan recipe for cpr 1.12.0 (C++ Requests / libcpr).

cpr is a thin C++17 wrapper around libcurl. The upstream CMakeLists prepends
its own cmake/ dir to CMAKE_MODULE_PATH, so the built-in find_package(OpenSSL)
and find_package(CURL) lookups bypass Conan's CMakeDeps config files. We feed
the built-in Find modules explicit OPENSSL_*/CURL_* cache variables pointing
into the Conan package folders instead of relying on config-mode discovery.
"""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    rmdir,
    unzip,
)


class CprConan(ConanFile):
    name = "cpr"
    version = "1.12.0"
    description = "C++ Requests: Curl for People, a spiritual port of Python Requests"
    license = "MIT"
    homepage = "https://github.com/libcpr/cpr"
    url = "https://github.com/libcpr/cpr"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cpr supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # curl/8.15.0 is the primary dependency. openssl + zlib are transitive
        # via curl, but must be declared as direct requirements as well so their
        # binaries are installed into the graph and self.dependencies["openssl"]
        # resolves a real package_folder during generate() (a transitive-only
        # lookup yields package_folder=None in the CI clean cache).
        # Versions MUST stay in sync with curl/8.15.0 (openssl/3.5.6.1,
        # zlib/1.3.1.1) — never bump to openssl/3.5.6.1.1 or zlib/1.3.2.
        self.requires("curl/8.15.0")
        self.requires("openssl/3.5.6.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        staged = os.path.join(os.path.expanduser("~"), "Download", source["filename"])
        if os.path.isfile(staged):
            check_sha256(self, staged, source["sha256"])
            unzip(self, staged, destination=self.source_folder, strip_root=True)
        else:
            get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # cpr's CMakeLists adds its own cmake/ dir to CMAKE_MODULE_PATH, after
        # which the built-in find_package(OpenSSL)/find_package(CURL) cannot see
        # the CMakeDeps config files. Set explicit cache variables pointing at the
        # Conan package dirs so the built-in Find modules succeed.
        curl = self.dependencies["curl"].cpp_info
        openssl = self.dependencies["openssl"].cpp_info

        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # CMake has no built-in HarmonyOS platform module. Complete its
            # shared-linker contract so shared cpr records a basename SONAME and
            # a build-only runtime path.
            for lang in ("C", "CXX"):
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_SONAME_{lang}_FLAG"
                ] = "-Wl,-soname,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{lang}_FLAG"
                ] = "-Wl,-rpath,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{lang}_FLAG_SEP"
                ] = ":"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{lang}_FLAG"
                ] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True

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
        tc.cache_variables["OPENSSL_USE_STATIC_LIBS"] = True
        # Conan CMakeDeps exposes OpenSSL in config mode, which sets the
        # `OpenSSL_FOUND` variable. cpr's CMakeLists checks the all-caps
        # `OPENSSL_FOUND` (a convention of the classic FindOpenSSL module),
        # so mark it explicitly now that the Conan OpenSSL package is wired.
        tc.cache_variables["OPENSSL_FOUND"] = True

        tc.cache_variables["CURL_ROOT_DIR"] = self.dependencies[
            "curl"
        ].package_folder
        tc.cache_variables["CURL_INCLUDE_DIR"] = curl.includedirs[0]
        tc.cache_variables["CURL_LIBRARY"] = os.path.join(
            curl.libdirs[0], "libcurl.so"
        )

        # cpr configuration: use the Conan-provided system curl/openssl, never
        # the FetchContent-bundled curl (network + fixed 8.13.0 version).
        tc.cache_variables["CPR_USE_SYSTEM_CURL"] = True
        tc.cache_variables["CPR_ENABLE_SSL"] = True
        tc.cache_variables["CPR_FORCE_OPENSSL_BACKEND"] = True
        tc.cache_variables["CPR_BUILD_TESTS"] = False
        tc.cache_variables["CPR_SKIP_CA_BUNDLE_SEARCH"] = False

        shared = bool(self.options.shared)
        tc.cache_variables["BUILD_SHARED_LIBS"] = shared
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = shared or bool(
            self.options.get_safe("fPIC", True)
        )

        # cpr's default -Werror on our clang is fine for the shipped sources,
        # but keep a tolerant baseline for toolchain header variations.
        tc.cache_variables["CMAKE_CXX_FLAGS"] = "-Wno-error"
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        # The upstream cprConfig.cmake does find_dependency(CURL REQUIRED) which
        # can conflict with Conan's CMakeDeps-driven consumers. Remove it; the
        # Conan package_info below drives the generated config instead.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

        # HarmonyOS refuses to map unsigned shared libraries (EACCES at load).
        # Sign every installed libcpr.so* exactly like other OHOS recipes do.
        if self.settings.os == "OHOS" and self.options.shared:
            libraries = glob.glob(
                os.path.join(self.package_folder, "lib", "**", "*.so*"),
                recursive=True,
            )
            self._sign_paths(libraries, required=False)

    def _sign_paths(self, paths, required):
        paths = sorted(
            {
                path
                for path in paths
                if os.path.isfile(path) and not os.path.islink(path)
            }
        )
        if not paths:
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            message = (
                "HarmonyOS execution requires llvm-objcopy and binary-sign-tool"
            )
            if required:
                raise ConanInvalidConfiguration(message)
            self.output.warning(
                f"{message}; release worker must sign the package"
            )
            return
        for path in paths:
            self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(shlex.join([objcopy, "--remove-section", ".codesign", temporary]))
            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        temporary,
                        "-outFile",
                        temporary,
                        "-selfSign",
                        "1",
                    ]
                )
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if os.path.isfile(path)), "")

    def package_info(self):
        self.cpp_info.libs = ["cpr"]
        # cpr links libcurl (CURL::libcurl) and the OpenSSL backend
        # (OpenSSL::SSL) at link time; zlib is a runtime dependency pulled in
        # through curl/openssl. All are declared as direct requirements, so
        # reference every one of them here (Conan 2.29 enforces that each
        # direct dependency is consumed by package_info).
        self.cpp_info.requires = [
            "curl::curl",
            "openssl::openssl",
            "zlib::zlib",
        ]
        self.cpp_info.set_property("cmake_file_name", "cpr")
        self.cpp_info.set_property("cmake_target_name", "cpr::cpr")
