# LLVMConfig.cmake — OHOS SDK LLVM overlay
# The OHOS SDK LLVM ships only monolithic libLLVM-15.so (no separate .a files).
# LLVMExports.cmake references .a files that don't exist, causing FATAL_ERROR.
# This overlay provides the LLVM configuration WITHOUT including the problematic
# LLVMExports.cmake, setting up the necessary targets manually.
#
# Usage: set LLVM_DIR to this directory before find_package(LLVM).

# ─── Locate the OHOS SDK LLVM installation ──────────────────────────
# Default prefix; may be overridden by OHOS_LLVM_DIR env var below.
set(_DEFAULT_LLVM_PREFIX "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm")

# Allow override via environment — recalculate ALL paths from the override.
if(DEFINED ENV{OHOS_LLVM_DIR} AND EXISTS "$ENV{OHOS_LLVM_DIR}/include")
    get_filename_component(LLVM_INSTALL_PREFIX "$ENV{OHOS_LLVM_DIR}" REALPATH)
else()
    get_filename_component(LLVM_INSTALL_PREFIX "${_DEFAULT_LLVM_PREFIX}" REALPATH)
endif()

# Recalculate derived paths from the (possibly overridden) prefix.
set(LLVM_CMAKE_DIR "${LLVM_INSTALL_PREFIX}/lib/cmake/llvm")
set(LLVM_INCLUDE_DIRS "${LLVM_INSTALL_PREFIX}/include")
set(LLVM_LIBRARY_DIR "${LLVM_INSTALL_PREFIX}/lib")
set(LLVM_TOOLS_BINARY_DIR "${LLVM_INSTALL_PREFIX}/bin")

# ─── LLVM version info ──────────────────────────────────────────────
set(LLVM_VERSION_MAJOR 15)
set(LLVM_VERSION_MINOR 0)
set(LLVM_VERSION_PATCH 4)
set(LLVM_PACKAGE_VERSION "15.0.4")
set(LLVM_BUILD_TYPE Release)
set(LLVM_PACKAGE_BUGREPORT "https://github.com/llvm/llvm-project/issues/")

# ─── LLVM definitions ───────────────────────────────────────────────
# Compatibility variable with -D prefix (used by other cmake modules).
set(LLVM_DEFINITIONS "-D__STDC_CONSTANT_MACROS -D__STDC_FORMAT_MACROS -D__STDC_LIMIT_MACROS")
# Target-usable definitions without -D prefix, semicolon-separated.
set(LLVM_COMPILE_DEFINITIONS "__STDC_CONSTANT_MACROS;__STDC_FORMAT_MACROS;__STDC_LIMIT_MACROS")
set(LLVM_ENABLE_ASSERTIONS OFF)
set(LLVM_ENABLE_EH OFF)
set(LLVM_ENABLE_RTTI OFF)
set(LLVM_ENABLE_TERMINFO OFF)
set(LLVM_ENABLE_THREADS ON)
set(LLVM_ENABLE_ZLIB OFF)
set(LLVM_ENABLE_ZSTD OFF)
set(LLVM_ENABLE_PLUGINS ON)

# ─── Target info ────────────────────────────────────────────────────
set(LLVM_TARGETS_TO_BUILD "AArch64;ARM;BPF;Mips;RISCV;X86;LoongArch")
set(LLVM_ALL_TARGETS "AArch64;AMDGPU;ARM;AVR;BPF;Hexagon;Lanai;LoongArch;Mips;MSP430;NVPTX;PowerPC;RISCV;Sparc;SystemZ;VE;WebAssembly;X86;XCore;XVM")
set(LLVM_TARGETS_WITH_JIT "X86;PowerPC;AArch64;ARM;Mips;SystemZ")

# ─── Monolithic shared library (contains all LLVM components) ───────
set(_LLVM_MONOLITHIC "${LLVM_LIBRARY_DIR}/libLLVM-15.so")
if(NOT EXISTS "${_LLVM_MONOLITHIC}")
    message(FATAL_ERROR "LLVM overlay: libLLVM-15.so not found at ${_LLVM_MONOLITHIC}")
endif()

# ─── Create LLVM imported target (the main library) ─────────────────
if(NOT TARGET LLVM)
    add_library(LLVM SHARED IMPORTED)
    set_target_properties(LLVM PROPERTIES
        IMPORTED_LOCATION "${_LLVM_MONOLITHIC}"
        INTERFACE_INCLUDE_DIRECTORIES "${LLVM_INCLUDE_DIRS}"
        INTERFACE_COMPILE_DEFINITIONS "${LLVM_COMPILE_DEFINITIONS}"
    )
endif()

# ─── Create LLVMDemangle target (missing .a, provided by monolithic .so) ──
if(NOT TARGET LLVMDemangle)
    add_library(LLVMDemangle UNKNOWN IMPORTED)
    set_target_properties(LLVMDemangle PROPERTIES
        IMPORTED_LOCATION "${_LLVM_MONOLITHIC}"
    )
endif()

# ─── Create LLVMSupport target (needed by Enzyme) ───────────────────
if(NOT TARGET LLVMSupport)
    add_library(LLVMSupport UNKNOWN IMPORTED)
    set_target_properties(LLVMSupport PROPERTIES
        IMPORTED_LOCATION "${_LLVM_MONOLITHIC}"
    )
endif()

# ─── Create LLVMCore target (needed by Enzyme) ──────────────────────
if(NOT TARGET LLVMCore)
    add_library(LLVMCore UNKNOWN IMPORTED)
    set_target_properties(LLVMCore PROPERTIES
        IMPORTED_LOCATION "${_LLVM_MONOLITHIC}"
    )
endif()

# ─── Create LLVMTransformUtils target (needed by Enzyme) ────────────
if(NOT TARGET LLVMTransformUtils)
    add_library(LLVMTransformUtils UNKNOWN IMPORTED)
    set_target_properties(LLVMTransformUtils PROPERTIES
        IMPORTED_LOCATION "${_LLVM_MONOLITHIC}"
    )
endif()

# ─── Create LLVMAnalysis target (needed by Enzyme) ──────────────────
if(NOT TARGET LLVMAnalysis)
    add_library(LLVMAnalysis UNKNOWN IMPORTED)
    set_target_properties(LLVMAnalysis PROPERTIES
        IMPORTED_LOCATION "${_LLVM_MONOLITHIC}"
    )
endif()

# ─── Set LLVM_LIBS for compatibility ────────────────────────────────
set(LLVM_LIBS "LLVM;LLVMDemangle;LLVMSupport;LLVMCore;LLVMTransformUtils;LLVMAnalysis")

# ─── Register targets ───────────────────────────────────────────────
set(LLVM_AVAILABLE_LIBS "LLVMDemangle;LLVMSupport;LLVMCore;LLVMTransformUtils;LLVMAnalysis")

# ─── Add LLVM cmake module path ─────────────────────────────────────
# The overlay directory contains a custom AddLLVM.cmake that provides
# the LLVM CMake functions needed by Enzyme without the incompatible
# OHOS SDK LLVM AddLLVM.cmake.
get_filename_component(_OVERLAY_DIR "${CMAKE_CURRENT_LIST_FILE}" PATH)
list(APPEND CMAKE_MODULE_PATH "${_OVERLAY_DIR}")

# ─── Set up TableGen support ────────────────────────────────────────
# OHOS SDK LLVM doesn't include llvm-tblgen binary. We provide a stub
# script that creates stub .inc files, allowing the build to proceed.
set(_STUB_TBLGEN "${_OVERLAY_DIR}/stub-tblgen.sh")
if(EXISTS "${_STUB_TBLGEN}")
    set(ENZYME_TABLEGEN_EXE "${_STUB_TBLGEN}")
    set(LLVM_TABLEGEN_EXE "${_STUB_TBLGEN}")
    set(ENZYME_TBLGEN_EXE "${_STUB_TBLGEN}")
    message(STATUS "LLVM overlay: Using stub tblgen: ${_STUB_TBLGEN}")
else()
    message(STATUS "LLVM overlay: stub-tblgen.sh not found at ${_STUB_TBLGEN}")
endif()

message(STATUS "LLVM overlay: OHOS SDK LLVM configured (version ${LLVM_PACKAGE_VERSION}, monolithic lib)")
message(STATUS "LLVM overlay: Targets: LLVM, LLVMDemangle, LLVMSupport, LLVMCore, LLVMTransformUtils, LLVMAnalysis")

# Clean up
unset(_LLVM_MONOLITHIC)
unset(_STUB_TBLGEN)
unset(_OVERLAY_DIR)