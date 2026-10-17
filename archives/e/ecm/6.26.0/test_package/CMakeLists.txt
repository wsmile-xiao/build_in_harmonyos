cmake_minimum_required(VERSION 3.16)
project(test_ecm)

find_package(ECM 6.26.0 EXACT REQUIRED NO_MODULE
    PATHS "${ECM_PACKAGE_PREFIX}/share/ECM/cmake"
    NO_DEFAULT_PATH
)
list(PREPEND CMAKE_MODULE_PATH "${ECM_MODULE_PATH}")
include(ECMFindModuleHelpers)

if(NOT COMMAND ecm_find_package_version_check)
    message(FATAL_ERROR "ECMFindModuleHelpers did not define ecm_find_package_version_check")
endif()
ecm_find_package_version_check(ECM)

if(NOT ECM_VERSION VERSION_EQUAL "6.26.0")
    message(FATAL_ERROR "Unexpected ECM version: ${ECM_VERSION}")
endif()
if(NOT EXISTS "${ECM_MODULE_DIR}/ECMFindModuleHelpers.cmake")
    message(FATAL_ERROR "ECM module directory is invalid: ${ECM_MODULE_DIR}")
endif()

add_executable(test_ecm test_ecm.cpp)
target_compile_definitions(test_ecm PRIVATE
    ECM_MODULE_HELPERS_LOADED=1
    ECM_VERSION_STRING="${ECM_VERSION}"
    ECM_MODULE_DIR_STRING="${ECM_MODULE_DIR}"
)

enable_testing()
add_test(NAME test_ecm_run COMMAND test_ecm)
