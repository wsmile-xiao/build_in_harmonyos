cmake_minimum_required(VERSION 3.21)
project(ohos_ecm_consumer LANGUAGES CXX)

# 真实消费者工程：消费 ECM 6.29.0 的实际模块
# 本测试在 OHOS 设备（aarch64-linux-ohos clang）上实际编译运行。
# 不使用 Qt 依赖模块，仅调用 ECM 提供的非 Qt 模块。

find_package(ECM 6.29.0 EXACT REQUIRED NO_MODULE
    PATHS "${ECM_PACKAGE_PREFIX}/share/ECM/cmake"
    NO_DEFAULT_PATH
)
list(PREPEND CMAKE_MODULE_PATH "${ECM_MODULE_PATH}")

# 模块 1: ECMFindModuleHelpers — 提供 ecm_find_package_version_check 等宏
include(ECMFindModuleHelpers)
if(NOT COMMAND ecm_find_package_version_check)
    message(FATAL_ERROR "ECMFindModuleHelpers did not define ecm_find_package_version_check")
endif()
ecm_find_package_version_check(ECM)

# 模块 2: ECMConfiguredInstall — 安装时替换 @VAR@ 变量
include(ECMConfiguredInstall)
if(NOT COMMAND ecm_install_configured_files)
    message(FATAL_ERROR "ECMConfiguredInstall did not define ecm_install_configured_files")
endif()

# 模块 3: ECMGenerateExportHeader — 生成真实导出头
include(ECMGenerateExportHeader)
add_library(ohos_dummy STATIC dummy.cpp)
ecm_generate_export_header(ohos_dummy
    BASE_NAME OHOSCONSUMER
    EXPORT_FILE_NAME "${CMAKE_CURRENT_BINARY_DIR}/generated/ohosconsumer_export.h"
    VERSION 6.29.0
    DEPRECATED_BASE_VERSION 5.0.0
    EXCLUDE_DEPRECATED_BEFORE_AND_AT 0
)
target_include_directories(ohos_dummy PUBLIC "${CMAKE_CURRENT_BINARY_DIR}/generated")

# 模块 4: ECMFeatureSummary — 摘要功能（此处仅验证模块可被 include 加载）
include(ECMFeatureSummary)
if(NOT COMMAND ecm_feature_summary)
    message(FATAL_ERROR "ECMFeatureSummary did not define ecm_feature_summary")
endif()

# 可执行文件（链接 ohos_dummy 以获取导出头）
add_executable(ohos_ecm_test main.cpp)
target_link_libraries(ohos_ecm_test PRIVATE ohos_dummy)
target_compile_definitions(ohos_ecm_test PRIVATE
    ECM_VERSION_STRING="${ECM_VERSION}"
    ECM_MODULE_DIR_STRING="${ECM_MODULE_DIR}"
)

enable_testing()
add_test(NAME ohos_ecm_test_run COMMAND ohos_ecm_test)