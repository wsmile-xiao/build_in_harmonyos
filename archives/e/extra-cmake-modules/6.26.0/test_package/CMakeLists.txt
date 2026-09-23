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

# .in 模板完整性断言（6.28.0 教训：缺失 .in 模板会导致下游
# include(ECMUninstallTarget)/ECMQmlModule configure 失败）
set(ECM_TEMPLATE_FILES
    "${ECM_MODULE_DIR}/ecm_uninstall.cmake.in"
    "${ECM_MODULE_DIR}/ECMVersionHeader.h.in"
    "${ECM_MODULE_DIR}/ECMQmlModule.cpp.in"
    "${ECM_MODULE_DIR}/ECMQmlModule.h.in"
    "${ECM_MODULE_DIR}/ECMQtDeclareLoggingCategory.cpp.in"
    "${ECM_MODULE_DIR}/ECMQtDeclareLoggingCategory.h.in"
    "${ECM_MODULE_DIR}/ECMQmLoader.cpp.in"
)
set(_template_count 0)
foreach(_tpl IN LISTS ECM_TEMPLATE_FILES)
    if(NOT EXISTS "${_tpl}")
        message(FATAL_ERROR "Missing ECM template file: ${_tpl}")
    endif()
    math(EXPR _template_count "${_template_count}+1")
endforeach()
message(STATUS "ECM .in templates verified: ${_template_count}/7")

# kde-modules / find-modules 目录断言
foreach(_dir "${ECM_KDE_MODULE_DIR}" "${ECM_FIND_MODULE_DIR}")
    if(NOT EXISTS "${_dir}")
        message(FATAL_ERROR "Missing ECM module directory: ${_dir}")
    endif()
endforeach()

add_executable(test_ecm test_ecm.cpp)
target_compile_definitions(test_ecm PRIVATE
    ECM_MODULE_HELPERS_LOADED=1
    ECM_VERSION_STRING="${ECM_VERSION}"
    ECM_MODULE_DIR_STRING="${ECM_MODULE_DIR}"
)

enable_testing()
add_test(NAME test_ecm_run COMMAND test_ecm)
