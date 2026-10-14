cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

# ============================================================
# (a) the package must be discoverable — find_package(ROCM REQUIRED)
# ============================================================
if(DEFINED ENV{ROCM_DIR})
    set(ROCM_DIR "$ENV{ROCM_DIR}")
    list(APPEND CMAKE_PREFIX_PATH "${ROCM_DIR}")
    list(APPEND CMAKE_MODULE_PATH "${ROCM_DIR}")
endif()

find_package(ROCM REQUIRED)

include(ROCMSetupVersion)
include(ROCMPackageConfigHelpers)
include(ROCMInstallTargets)

# ============================================================
# (b1) real API #1: rocm_setup_version sets <PROJECT_NAME>_VERSION
# ============================================================
rocm_setup_version(VERSION 0.4.0)
if(NOT test_package_VERSION VERSION_EQUAL "0.4.0")
    message(FATAL_ERROR
        "rocm_setup_version failed: expected 0.4.0, got '${test_package_VERSION}'")
endif()

# ============================================================
# (b2) real API #2: rocm_get_patch_version reads ROCM_LIBPATCH_VERSION
# ============================================================
rocm_get_patch_version(ROCM_PATCH_VALUE)
if(NOT ROCM_PATCH_VALUE STREQUAL "0")
    message(FATAL_ERROR
        "rocm_get_patch_version failed: expected '0', got '${ROCM_PATCH_VALUE}'")
endif()

# ============================================================
# (b3) real API #3: install a library and export its CMake package config
# ============================================================
include(GNUInstallDirs)

# rocm_consumer_core: a real static library built from test_package.cpp.
add_library(rocm_consumer_core STATIC test_package.cpp)
target_compile_definitions(rocm_consumer_core PRIVATE ROCM_CONSUMER_LIBRARY_ONLY)

# consumer executable that links the library above.
add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE rocm_consumer_core)
target_compile_definitions(test_package PRIVATE
    ROCM_CONSUMER_VERSION="${test_package_VERSION}"
    ROCM_CONSUMER_PATCH="${ROCM_PATCH_VALUE}")

# rocm_install_targets installs the library; rocm_export_targets generates and
# installs the CMake package config for it.
rocm_install_targets(TARGETS rocm_consumer_core)
rocm_export_targets(NAMESPACE rocm_consumer:: TARGETS rocm_consumer_core)

# ============================================================
# (c) hard failure if the exported config was not actually produced
# ============================================================
set(_expected_config "${CMAKE_CURRENT_BINARY_DIR}/test_package-config.cmake")
if(NOT EXISTS "${_expected_config}")
    message(FATAL_ERROR
        "rocm_export_targets did not produce ${_expected_config}")
endif()

install(CODE "
    if(NOT EXISTS \"\${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}/librocm_consumer_core.a\")
        message(FATAL_ERROR \"rocm_install_targets did not install the library\")
    endif()
    if(NOT EXISTS \"\${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}/cmake/test_package/test_package-config.cmake\")
        message(FATAL_ERROR \"rocm_export_targets did not install the package config\")
    endif()
")
