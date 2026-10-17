#!/usr/bin/env python3
"""Conan recipe — xeus 6.0.5 (C++ Jupyter Kernel protocol library)

xeus is a C++ library implementing the Jupyter Kernel protocol, enabling
developers to focus on the interpreter part of Jupyter kernels.

Build system: CMake (3.16+)
License: BSD-3-Clause
Homepage: https://github.com/jupyter-xeus/xeus

Dependencies:
  - nlohmann_json >= 3.11.2 (header-only JSON, required)
  - libuuid (Unix UUID generation via GUID_LIBUUID, required on Linux/OHOS)

Adaptation notes (HarmonyOS PC, aarch64):
  * W0: nlohmann_json/3.12.0 and libuuid/2.42.2 are published on ohpcd
    with OHOS armv8 binaries (verified via conan download).
  * Build static library only (shared libs problematic on OHOS due to
    SONAME versioning and rpath constraints). XEUS_BUILD_SHARED_LIBS=OFF.
  * CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY: CI workers' lld has
    broken runtime dependency on libxml2.so.16, causing try_compile to
    fail before the real build starts. STATIC_LIBRARY uses ar instead.
  * XEUS_BUILD_TESTS disabled in default build; upstream tests run
    separately with doctest (see test_package/MANIFEST.yml).
  * Compiler warnings (CompilerWarnings.cmake) set -Werror via
    xeus_target_add_compile_warnings(WARNING_AS_ERROR) for some flags.
    On OHOS with clang 15 some conversions trigger warnings that
    upstream's warning-as-error would catch; we disable warnings-as-error
    via CMake variable to avoid build breaks on borderline cases.
  * xeusConfig.cmake.in uses find_dependency(LibUUID) on Unix (non-Apple).
    Conan libuuid provides cmake_target_name=LibUUID::LibUUID which
    satisfies the find_dependency call.
  * No patches: upstream CMakeLists.txt cross-compiles cleanly with
    standard toolchain. OHOS is treated as Linux by CMake, which is
    correct for our use case (same ABI, same libuuid API).

Artifacts: include/xeus/*.h, lib/libxeus.a (static)
License: BSD-3-Clause
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class XeusConan(ConanFile):
    name = "xeus"
    version = "6.0.5"
    description = "C++ implementation of the Jupyter Kernel protocol"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jupyter-xeus/xeus"
    url = "https://github.com/jupyter-xeus/xeus"
    topics = ("jupyter", "kernel", "protocol", "cpp", "header-only-json")
    package_type = "library"

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

    def layout(self):
        # cmake_layout expects a specific src_folder structure; for xeus
        # the CMakeLists.txt is at the root, so we use basic_layout and
        # point CMakeToolchain at source_folder directly.
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xeus supports Linux and OHOS, got {self.settings.os}"
            )
        if self.settings.compiler.cppstd:
            cppstd = str(self.settings.compiler.cppstd)
            if cppstd not in ("17", "20", "23", "gnu17", "gnu20", "gnu23"):
                raise ConanInvalidConfiguration(
                    f"xeus requires C++17, got {cppstd}"
                )

    def requirements(self):
        # nlohmann_json: required for JSON message encoding/decoding
        # in the Jupyter kernel protocol. Header-only.
        self.requires("nlohmann_json/3.12.0")
        # libuuid: required on Unix (non-Apple) for GUID generation
        # (GUID_LIBUUID path). Provides uuid/uuid.h.
        if self.settings.os in ("Linux", "OHOS"):
            self.requires("libuuid/2.42.2")

    def source(self):
        # conandata.yml has version-nested sources: sources["6.0.5"]["url"]
        data = self.conan_data["sources"]
        if self.version in data:
            data = data[self.version]
        get(self, url=data["url"], sha256=data["sha256"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # Build static library only. Shared libs on OHOS have SONAME/rpath
        # complications that xeus's CMakeLists doesn't handle well.
        tc.variables["XEUS_BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["XEUS_BUILD_STATIC_LIBS"] = "ON"
        tc.variables["XEUS_BUILD_TESTS"] = "OFF"

        # Skip the linking step in CMake try_compile (compiler detection).
        # On CI the lld linker from the OHOS SDK fails to load
        # libxml2.so.16, causing try_compile to fail before the real build.
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"

        # Disable warnings-as-error: upstream's CompilerWarnings.cmake
        # sets -Werror for some flags, which breaks on borderline
        # conversions in clang 15 with our headers. Full warnings still
        # apply; just not fatal.
        tc.variables["XEUS_WARNING_AS_ERROR"] = "OFF"

        # OHOS doesn't have the same GUID generation as Linux, but the
        # libuuid API is available. Keep GUID_LIBUUID defined.
        tc.variables["CMAKE_BUILD_TYPE"] = str(self.settings.build_type)

        tc.generate()

        # nlohmann_json on ohpcd is header-only and doesn't ship cmake config
        # files. Create minimal nlohmann_jsonConfig.cmake and ConfigVersion
        # files so xeus's find_package(nlohmann_json 3.11) works.
        nlohmann_dep = self.dependencies["nlohmann_json"]
        nlohmann_include = None
        for inc_dir in nlohmann_dep.cpp_info.includedirs:
            full_path = os.path.join(nlohmann_dep.package_folder, inc_dir)
            if os.path.isdir(os.path.join(full_path, "nlohmann")):
                nlohmann_include = full_path
                break
        if nlohmann_include is None:
            nlohmann_include = os.path.join(nlohmann_dep.package_folder, "include")

        include_dir = nlohmann_include.replace("\\", "/")
        config_file = os.path.join(self.generators_folder, "nlohmann_jsonConfig.cmake")
        with open(config_file, "w") as f:
            f.write("""# Auto-generated nlohmann_jsonConfig.cmake
set(nlohmann_json_FOUND TRUE)
set(nlohmann_json_VERSION "3.12.0")
if(NOT TARGET nlohmann_json::nlohmann_json)
    add_library(nlohmann_json::nlohmann_json INTERFACE IMPORTED)
    set_target_properties(nlohmann_json::nlohmann_json PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "{include_dir}"
    )
endif()
""".format(include_dir=include_dir))

        # ConfigVersion.cmake is required by find_package for version checking
        version_file = os.path.join(self.generators_folder, "nlohmann_jsonConfigVersion.cmake")
        with open(version_file, "w") as f:
            f.write("""# Auto-generated nlohmann_jsonConfigVersion.cmake
set(PACKAGE_VERSION "3.12.0")
if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)
    set(PACKAGE_VERSION_COMPATIBLE FALSE)
else()
    set(PACKAGE_VERSION_COMPATIBLE TRUE)
    if(PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)
        set(PACKAGE_VERSION_EXACT TRUE)
    endif()
endif()
""")

        # Ensure lld (used by clang for linking) can locate its runtime
        # dependency libxml2.so.16. Same workaround as x265/4.2.
        env = Environment()
        lld_path = shutil.which("lld") or shutil.which("ld")
        if lld_path:
            lld_real = os.path.realpath(lld_path)
            sdk_lib = os.path.normpath(
                os.path.join(os.path.dirname(lld_real), "..", "lib")
            )
            if os.path.isdir(sdk_lib):
                env.append("LD_LIBRARY_PATH", sdk_lib)
        env.vars(self, scope="build").save_script("conan_lld_fix")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Copy license
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # CMake find_package names
        self.cpp_info.set_property("cmake_file_name", "xeus")
        self.cpp_info.set_property("cmake_target_name", "xeus::xeus")
        self.cpp_info.set_property("pkg_config_name", "xeus")

        # Library name: xeus (static lib on OHOS)
        self.cpp_info.libs = ["xeus"]

        # System libraries needed by consumers
        self.cpp_info.system_libs = ["pthread"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("uuid")

        # Transitive requirements: consumers need nlohmann_json headers
        # to exchange JSON objects with the same version.
        self.cpp_info.requires = [
            "nlohmann_json::nlohmann_json",
            "libuuid::libuuid",
        ]

        # Include directories
        self.cpp_info.includedirs = ["include"]

        # Library directories
        self.cpp_info.libdirs = ["lib"]

        # Bindirs (empty for library-only package)
        self.cpp_info.bindirs = []

        # Propagate LD_LIBRARY_PATH for lld runtime dependency
        lld_path = shutil.which("lld") or shutil.which("ld")
        if lld_path:
            lld_real = os.path.realpath(lld_path)
            sdk_lib = os.path.normpath(
                os.path.join(os.path.dirname(lld_real), "..", "lib")
            )
            if os.path.isdir(sdk_lib):
                self.buildenv_info.append("LD_LIBRARY_PATH", sdk_lib)
