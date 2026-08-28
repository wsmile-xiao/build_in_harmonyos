cmake_minimum_required(VERSION 3.16)
project(test_ecm C)

# ECM 是纯 cmake 模块包，不编译任何代码
# 验证 find_package(ECM) 和所有关键 ECM 模块可用
find_package(ECM REQUIRED CONFIG)

message(STATUS "ECM Version: ${ECM_VERSION}")
message(STATUS "ECM_MODULE_DIR: ${ECM_MODULE_DIR}")

# ============================================================
# 1. 核心 ECM 模块文件存在性验证
#    对应上游 ExecuteCoreModules + ExecuteKDEModules 测试
# ============================================================
set(ECM_CORE_MODULES
    ECMSetupVersion.cmake
    ECMGenerateExportHeader.cmake
    ECMGeneratePkgConfigFile.cmake
    ECMAddTests.cmake
    ECMMarkNonGuiExecutable.cmake
)
set(ECM_KDE_MODULES
    KDEInstallDirs.cmake
    KDECMakeSettings.cmake
    KDECompilerSettings.cmake
    KDEFrameworkCompilerSettings.cmake
)

set(_core_count 0)
set(_kde_count 0)
set(_include_count 0)
set(_dir_count 0)

# 1. Core module file checks (each FATAL_ERROR on failure)
foreach(_mod IN LISTS ECM_CORE_MODULES)
    if(EXISTS "${ECM_MODULE_DIR}${_mod}")
        file(READ "${ECM_MODULE_DIR}${_mod}" _mod_content LIMIT 1)
        math(EXPR _core_count "${_core_count}+1")
        message(STATUS "  ✅ core module: ${_mod}")
    else()
        message(FATAL_ERROR "Missing core ECM module: ${_mod}")
    endif()
endforeach()

# 2. KDE module file checks (each FATAL_ERROR on failure)
foreach(_mod IN LISTS ECM_KDE_MODULES)
    if(EXISTS "${ECM_KDE_MODULE_DIR}/${_mod}")
        math(EXPR _kde_count "${_kde_count}+1")
        message(STATUS "  ✅ KDE module: ${_mod}")
    else()
        message(FATAL_ERROR "Missing KDE ECM module: ${_mod}")
    endif()
endforeach()

# 3. Include checks — real API call (each include fails CMake on error)
include(ECMSetupVersion)
math(EXPR _include_count "${_include_count}+1")
message(STATUS "  ✅ included: ECMSetupVersion")

include(ECMGenerateExportHeader)
math(EXPR _include_count "${_include_count}+1")
message(STATUS "  ✅ included: ECMGenerateExportHeader")

include(ECMGeneratePkgConfigFile)
math(EXPR _include_count "${_include_count}+1")
message(STATUS "  ✅ included: ECMGeneratePkgConfigFile")

include(ECMAddTests)
math(EXPR _include_count "${_include_count}+1")
message(STATUS "  ✅ included: ECMAddTests")

# 4. Directory checks (FATAL_ERROR on failure)
if(EXISTS "${ECM_FIND_MODULE_DIR}")
    math(EXPR _dir_count "${_dir_count}+1")
    message(STATUS "  ✅ find-modules dir: ${ECM_FIND_MODULE_DIR}")
else()
    message(FATAL_ERROR "Missing ECM find-modules directory")
endif()

if(EXISTS "${ECM_KDE_MODULE_DIR}")
    math(EXPR _dir_count "${_dir_count}+1")
    message(STATUS "  ✅ kde-modules dir: ${ECM_KDE_MODULE_DIR}")
else()
    message(FATAL_ERROR "Missing ECM kde-modules directory")
endif()

math(EXPR _total_assertions "${_core_count}+${_kde_count}+${_include_count}+${_dir_count}")

# 5. Write verification marker — only reached if ALL checks passed
file(WRITE "${CMAKE_BINARY_DIR}/ecm_verified"
    "ecm_verified=${_total_assertions}\n"
    "ecm_version=${ECM_VERSION}\n"
    "core_modules_checked=${_core_count}\n"
    "kde_modules_checked=${_kde_count}\n"
    "includes_checked=${_include_count}\n"
    "directories_checked=${_dir_count}\n"
)

message(STATUS "ECM test_package: find_package(ECM) + ${_total_assertions} assertions OK")
