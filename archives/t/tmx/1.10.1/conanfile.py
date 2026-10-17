#!/usr/bin/env python3
"""Conan recipe -- tmx 1.10.1 (cmake, C library for Tiled maps)."""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)


class TmxConan(ConanFile):
    name = "tmx"
    version = "1.10.1"
    description = "Portable C library to load Tiled maps in games"
    license = "BSD-2-Clause"
    homepage = "https://github.com/baylej/tmx"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Upstream CMakeLists: LibXml2 REQUIRED, ZLIB REQUIRED when
        # WANT_ZLIB=ON (default). zstd stays OFF (WANT_ZSTD default Off).
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tmx is adapted for Linux and OHOS, not {}".format(
                    self.settings.os
                )
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_executable(self, key, fallback_name):
        # The ohos-aarch64 profile pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang(++), but that file may not exist on the
        # current preflight worker (then both CMAKE_C/CXX_COMPILER sanity
        # checks fail inside project()). Resolve to an existing binary, else
        # fall back to a PATH lookup (hmbs prepends its tool dirs to the
        # buildenv PATH). Only the executable is switched; no flag changes.
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)

    def generate(self):
        # Standard CMakeToolchain + CMakeDeps (ADAPTATION_GUIDE 4.2).
        # The previous self-discovered ohos.toolchain.cmake + raw cmake route
        # hard-fails on preflight workers where profile user_toolchain and
        # OHOS_NDK_HOME are both unset and the /data/service/hnp SDK glob
        # has no hit (Invalid configuration: ohos.toolchain.cmake not
        # found). The standard chain carries the OHOS profile compiler and
        # HarmonyOS system name without any external SDK file dependency
        # (same lesson as tvm-ffi: textparser/1.9.0 passes with the standard
        # chain; "System is unknown to cmake" is warning-level only).
        deps = CMakeDeps(self)
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.set_property("libxml2", "cmake_file_name", "LibXml2")
        deps.set_property("libxml2", "cmake_target_name", "LibXml2::LibXml2")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe(
            "fPIC", True
        )
        tc.variables["WANT_ZLIB"] = "ON"
        tc.variables["WANT_ZSTD"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # Route upstream module-mode find_package(ZLIB/LibXml2) through the
        # CMakeDeps-generated configs so no host copy leaks in via sysroot.
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        if str(self.settings.get_safe("os")) == "OHOS":
            # Force the resolved compilers through cache variables as well:
            # the generated toolchain file otherwise bakes the
            # profile-pinned absolute paths verbatim (missing file on some
            # workers makes project() fail its compiler sanity check).
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable(
                "c", "clang"
            )
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable(
                "cpp", "clang++"
            )
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Serialize the library build: preflight hit Signal 9 (SIGKILL,
        # consistent with fork/memory pressure on the shared worker) while
        # compiling this tiny 6-TU library. Force -j1 so the build stays
        # serial even if tools.build:jobs is ever unset; library sources,
        # flags and optimization are unchanged.
        cmake.build(cli_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # HarmonyOS PC XPM requires dlopen'ed .so files to carry a valid
        # code signature; the SDK toolchain output self-sign is not valid
        # after conan install copies, so re-sign here. No-op for the
        # default static build (no .so files present).
        libdir = os.path.join(self.package_folder, "lib")
        targets = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        targets += glob.glob(
            os.path.join(libdir, "**", "*.so.*"), recursive=True
        )
        if not targets:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" '
                "2>/dev/null || true".format(oc=objcopy, f=target)
            )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=target
                )
            )

    def package_info(self):
        self.cpp_info.libs = ["tmx"]
        self.cpp_info.set_property("cmake_file_name", "tmx")
        self.cpp_info.set_property("cmake_target_name", "tmx::tmx")
        # Upstream links both dependencies publicly
        # (target_link_libraries without PRIVATE).
        self.cpp_info.requires = ["libxml2::libxml2", "zlib::zlib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
