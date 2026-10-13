cmake_minimum_required(VERSION 3.16)
project(test_rocm_core LANGUAGES CXX)

# Resolve the package through Conan's generated CMakeDeps config.
find_package(rocm-core CONFIG REQUIRED)

add_executable(test_rocm_core test_rocm_core.cpp)
target_link_libraries(test_rocm_core PRIVATE rocm-core::rocm-core)

# HarmonyOS-specific complete consumer flows (rule 12), built only for OHOS.
# conanfile.py sets ROCM_CORE_TEST_OHOS when settings.os == "OHOS"; the source
# also carries its own #ifndef __OHOS__ #error guard.
option(ROCM_CORE_TEST_OHOS "Build the HarmonyOS-specific complete consumer flows" OFF)
if(ROCM_CORE_TEST_OHOS)
    add_executable(test_rocm_core_ohos test_rocm_core_ohos.cpp)
    target_link_libraries(test_rocm_core_ohos PRIVATE rocm-core::rocm-core)
endif()

enable_testing()
add_test(NAME test_rocm_core COMMAND test_rocm_core)
