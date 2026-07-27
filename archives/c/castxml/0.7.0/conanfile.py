#!/usr/bin/env python3
"""Conan recipe for CastXML — C-family abstract syntax tree XML output tool.

CastXML requires LLVM/Clang development libraries at build time.
On OHOS, LLVM/Clang is provided by the SDK at the standard toolchain path.

Usage: conan create . -pr=ohos-aarch64
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building
from conan.tools.env import Environment
import os
import subprocess


class CastxmlConan(ConanFile):
    name = "castxml"
    version = "0.7.0"
    description = "C-family abstract syntax tree XML output tool"
    license = "Apache-2.0"
    homepage = "https://github.com/CastXML/CastXML"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # LLVM/Clang from OHOS SDK — use OHOS_SDK_LLVM_ROOT env var, fallback to standard path
        llvm_root = os.environ.get("OHOS_SDK_LLVM_ROOT",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm")
        if not os.path.exists(os.path.join(llvm_root, "bin", "clang")):
            raise ConanException(
                f"OHOS SDK LLVM root not found at {llvm_root}. "
                "Set OHOS_SDK_LLVM_ROOT environment variable to the correct LLVM path.")

        # Create a custom __config_site to override ABI namespace to __h
        # (matches the SDK's LLVM shared libraries)
        config_site_dir = os.path.join(self.build_folder, "custom-config")
        os.makedirs(config_site_dir, exist_ok=True)
        config_site = os.path.join(config_site_dir, "__config_site")
        save(self, config_site, """// Custom __config_site — override ABI namespace to __h
#ifndef _LIBCPP___CONFIG_SITE
#define _LIBCPP___CONFIG_SITE
#define _LIBCPP_ABI_VERSION 1
#define _LIBCPP_ABI_NAMESPACE __h
#define _LIBCPP_HAS_NO_VENDOR_AVAILABILITY_ANNOTATIONS
#define _LIBCPP_ENABLE_ASSERTIONS_DEFAULT 0
#endif
""")

        # Add custom config dir to include paths
        tc.variables["CMAKE_CXX_FLAGS"] = "-I" + config_site_dir

        # Create a patched cmake config directory for both LLVM and Clang
        patch_dir = os.path.join(self.build_folder, "llvm-patch", "lib", "cmake")
        llvm_patch_dir = os.path.join(patch_dir, "llvm")
        clang_patch_dir = os.path.join(patch_dir, "clang")
        os.makedirs(llvm_patch_dir, exist_ok=True)
        os.makedirs(clang_patch_dir, exist_ok=True)

        # Write a simplified LLVMConfig.cmake
        llvm_config = []
        llvm_config.append('set(LLVM_INSTALL_PREFIX "{}")'.format(llvm_root))
        llvm_config.append('set(LLVM_VERSION_MAJOR 15)')
        llvm_config.append('set(LLVM_VERSION_MINOR 0)')
        llvm_config.append('set(LLVM_VERSION_PATCH 4)')
        llvm_config.append('set(LLVM_VERSION_STRING "15.0.4")')
        llvm_config.append('set(LLVM_PACKAGE_VERSION 15.0.4)')
        llvm_config.append('set(LLVM_BUILD_TYPE Release)')
        llvm_config.append('set(LLVM_ENABLE_SHARED_LIBS ON)')
        llvm_config.append('set(LLVM_ENABLE_EH OFF)')
        llvm_config.append('set(LLVM_ENABLE_RTTI OFF)')
        llvm_config.append('set(LLVM_ON_UNIX 1)')
        llvm_config.append('set(LLVM_NATIVE_ARCH AArch64)')
        llvm_config.append('set(LLVM_TARGET_TRIPLE "aarch64-linux-ohos")')
        llvm_config.append('set(LLVM_HOST_TRIPLE "aarch64-linux-ohos")')
        llvm_config.append('set(LLVM_INCLUDE_DIRS "${LLVM_INSTALL_PREFIX}/include")')
        llvm_config.append('set(LLVM_INCLUDE_DIR "${LLVM_INSTALL_PREFIX}/include")')
        llvm_config.append('set(LLVM_LIBRARY_DIRS "${LLVM_INSTALL_PREFIX}/lib")')
        llvm_config.append('set(LLVM_LIBRARY_DIR "${LLVM_INSTALL_PREFIX}/lib")')
        llvm_config.append('set(LLVM_BINARY_DIR "${LLVM_INSTALL_PREFIX}")')
        llvm_config.append('set(LLVM_TOOLS_BINARY_DIR "${LLVM_INSTALL_PREFIX}/bin")')
        llvm_config.append('set(LLVM_DEFINITIONS "-D__STDC_CONSTANT_MACROS -D__STDC_FORMAT_MACROS -D__STDC_LIMIT_MACROS")')
        llvm_config.append('set(LLVM_CMAKE_DIR "${CMAKE_CURRENT_LIST_DIR}")')
        llvm_config.append('set(LLVM_DYLIB_COMPONENTS all)')
        llvm_config.append('set(LLVM_AVAILABLE_LIBS "LLVMDemangle;LLVMSupport;LLVMTableGen;LLVMCore;LLVMBinaryFormat;LLVMBitReader;LLVMBitWriter;LLVMBitstreamReader;LLVMTransformUtils;LLVMInstrumentation;LLVMInstCombine;LLVMScalarOpts;LLVMipo;LLVMVectorize;LLVMLinker;LLVMAnalysis;LLVMMC;LLVMMCParser;LLVMMCDisassembler;LLVMObject;LLVMObjectYAML;LLVMOption;LLVMRemarks;LLVMDebugInfoDWARF;LLVMDebugInfoGSYM;LLVMDebugInfoCodeView;LLVMDebugInfoPDB;LLVMSymbolize;LLVMExecutionEngine;LLVMTarget;LLVMAsmParser;LLVMProfileData;LLVMPasses;LLVMTextAPI;LLVMCodeGen;LLVMSelectionDAG;LLVMAsmPrinter;LLVMMIRParser;LLVMGlobalISel")')
        llvm_config.append('set(LLVM_TARGETS_TO_BUILD "")')
        llvm_config.append('set_property(GLOBAL PROPERTY LLVM_TARGETS_CONFIGURED On)')
        llvm_config.append('set(LLVM_FOUND TRUE)')
        llvm_config.append('')
        llvm_config.append('# Create the LLVM shared library target (needed by llvm_config)')
        llvm_config.append('if(NOT TARGET LLVM)')
        llvm_config.append('  add_library(LLVM SHARED IMPORTED)')
        llvm_config.append('  set_target_properties(LLVM PROPERTIES')
        llvm_config.append('    IMPORTED_LOCATION "${LLVM_INSTALL_PREFIX}/lib/libLLVM-15.0.4.so"')
        llvm_config.append('    INTERFACE_INCLUDE_DIRECTORIES "${LLVM_INCLUDE_DIRS}"')
        llvm_config.append('  )')
        llvm_config.append('endif()')
        llvm_config.append('')
        llvm_config.append('# Include LLVM-Config.cmake to get llvm_config macro')
        llvm_config.append('include("${CMAKE_CURRENT_LIST_DIR}/LLVM-Config.cmake")')
        save(self, os.path.join(llvm_patch_dir, "LLVMConfig.cmake"), "\n".join(llvm_config))

        # Copy LLVM-Config.cmake from the SDK
        sdk_llvm_config = os.path.join(llvm_root, "lib", "cmake", "llvm", "LLVM-Config.cmake")
        if os.path.exists(sdk_llvm_config):
            with open(sdk_llvm_config) as f:
                save(self, os.path.join(llvm_patch_dir, "LLVM-Config.cmake"), f.read())

        # Write a simplified ClangConfig.cmake that doesn't need static libs
        clang_config = []
        clang_config.append('set(CLANG_INSTALL_PREFIX "{}")'.format(llvm_root))
        clang_config.append('set(CLANG_VERSION_MAJOR 15)')
        clang_config.append('set(CLANG_VERSION_MINOR 0)')
        clang_config.append('set(CLANG_VERSION_PATCH 4)')
        clang_config.append('set(CLANG_VERSION_STRING "15.0.4")')
        clang_config.append('set(CLANG_INCLUDE_DIRS "${CLANG_INSTALL_PREFIX}/include")')
        clang_config.append('set(CLANG_INCLUDE_DIR "${CLANG_INSTALL_PREFIX}/include")')
        clang_config.append('')
        clang_config.append('set(LLVM_DIR "{}")'.format(llvm_patch_dir))
        clang_config.append('include("${LLVM_DIR}/LLVMConfig.cmake")')
        clang_config.append('')
        clang_config.append('if(NOT TARGET clang-cpp)')
        clang_config.append('  add_library(clang-cpp SHARED IMPORTED)')
        clang_config.append('  set_target_properties(clang-cpp PROPERTIES')
        clang_config.append('    IMPORTED_LOCATION "${CLANG_INSTALL_PREFIX}/lib/libclang-cpp.so"')
        clang_config.append('    INTERFACE_INCLUDE_DIRECTORIES "${CLANG_INCLUDE_DIRS}"')
        clang_config.append('  )')
        clang_config.append('endif()')
        clang_config.append('')
        clang_config.append('# Also create individual clang lib targets for non-dylib path')
        clang_config.append('foreach(_clanglib clangFrontend clangDriver clangSerialization clangParse clangSema clangAnalysis clangEdit clangAST clangLex clangBasic)')
        clang_config.append('  if(NOT TARGET ${_clanglib})')
        clang_config.append('    add_library(${_clanglib} SHARED IMPORTED)')
        clang_config.append('    set_target_properties(${_clanglib} PROPERTIES')
        clang_config.append('      IMPORTED_LOCATION "${CLANG_INSTALL_PREFIX}/lib/libclang-cpp.so"')
        clang_config.append('      INTERFACE_INCLUDE_DIRECTORIES "${CLANG_INCLUDE_DIRS}"')
        clang_config.append('    )')
        clang_config.append('  endif()')
        clang_config.append('endforeach()')
        clang_config.append('')
        clang_config.append('set(CLANG_FOUND TRUE)')
        save(self, os.path.join(clang_patch_dir, "ClangConfig.cmake"), "\n".join(clang_config))

        # Point to the patched LLVM and Clang configs
        tc.variables["LLVM_DIR"] = llvm_patch_dir
        tc.variables["Clang_DIR"] = clang_patch_dir

        # Use shared LLVM/Clang libraries (both required by CastXML's CMake check)
        # Note: LLVM_LINK_LLVM_DYLIB + CLANG_LINK_CLANG_DYLIB causes duplicate
        # CommandLine option registration (known limitation on OHOS shared libs)
        tc.variables["LLVM_LINK_LLVM_DYLIB"] = "ON"
        tc.variables["CLANG_LINK_CLANG_DYLIB"] = "ON"

        # Enable testing for recipe build
        tc.variables["BUILD_TESTING"] = "ON"

        # Set C++ standard explicitly (E096)
        tc.variables["CMAKE_CXX_STANDARD"] = "14"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # ── Diagnostics: LLVM/Clang runtime library resolution ──
        llvm_root = os.environ.get("OHOS_SDK_LLVM_ROOT",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm")
        self.output.info("=" * 60)
        self.output.info("CTEST DIAGNOSTICS: LLVM/Clang runtime library resolution")
        self.output.info(f"LLVM_ROOT={llvm_root}")
        self.output.info(f"LLVM_LIB_DIR={llvm_root}/lib")
        self.output.info(f"LIBCPP_DIR={llvm_root}/lib/aarch64-linux-ohos/c++")
        self.output.info("--- find libLLVM-15.so ---")
        self.run(f"find {llvm_root}/lib -name 'libLLVM-15*' 2>/dev/null || echo 'NOT FOUND'")
        self.output.info("--- find libclang-cpp.so ---")
        self.run(f"find {llvm_root}/lib -name 'libclang-cpp*' 2>/dev/null || echo 'NOT FOUND'")
        self.output.info("--- find libc++.so ---")
        self.run(f"find {llvm_root}/lib -name 'libc++*' 2>/dev/null || echo 'NOT FOUND'")
        self.output.info("--- find libc++abi.so ---")
        self.run(f"find {llvm_root}/lib -name 'libc++abi*' 2>/dev/null || echo 'NOT FOUND'")
        self.output.info("--- castxml binary readelf -d ---")
        castxml_bin = os.path.join(self.build_folder, "build", "Release", "bin", "castxml")
        if os.path.exists(castxml_bin):
            self.run(f"readelf -d '{castxml_bin}' 2>/dev/null || echo 'readelf failed'")
            self.run(f"readelf -l '{castxml_bin}' 2>/dev/null | grep -E 'interp|INTERP' || echo 'no interpreter'")
        else:
            alt_bin = os.path.join(self.build_folder, "bin", "castxml")
            if os.path.exists(alt_bin):
                self.run(f"readelf -d '{alt_bin}' 2>/dev/null || echo 'readelf failed'")
            else:
                self.output.info("castxml binary not found at expected paths")
                self.run(f"find {self.build_folder} -name 'castxml' -type f 2>/dev/null || echo 'not found anywhere'")
        self.output.info("=" * 60)

        # Run upstream tests (ctest) with LD_LIBRARY_PATH set for LLVM/Clang shared libs
        env = Environment()
        env.append_path("LD_LIBRARY_PATH", os.path.join(llvm_root, "lib"))
        env.append_path("LD_LIBRARY_PATH", os.path.join(llvm_root, "lib", "aarch64-linux-ohos", "c++"))
        with env.vars(self).apply():
            result = subprocess.run(
                ["ctest", "--output-on-failure"],
                cwd=self.build_folder,
                check=False,
            )
            if result.returncode != 0:
                raise ConanException(f"ctest failed with exit code {result.returncode}")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        # R38: This is a command-line tool
        # Binary: castxml

        # Set runtime library paths for LLVM/Clang shared libs
        llvm_root = os.environ.get("OHOS_SDK_LLVM_ROOT",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm")
        self.runenv_info.append("LD_LIBRARY_PATH", f"{llvm_root}/lib:{llvm_root}/lib/aarch64-linux-ohos/c++")
        self.buildenv_info.append("LD_LIBRARY_PATH", f"{llvm_root}/lib:{llvm_root}/lib/aarch64-linux-ohos/c++")