cmake_minimum_required(VERSION 3.15)
project(test_package)

# 使用 ROCM_DIR 环境变量查找 ROCMConfig.cmake（加引号避免路径含空格被拆分）
if(DEFINED ENV{ROCM_DIR})
    set(ROCM_DIR "$ENV{ROCM_DIR}")
    list(APPEND CMAKE_PREFIX_PATH "${ROCM_DIR}")
endif()

find_package(ROCM REQUIRED)

# ===== 鸿蒙消费者测试：实际调用 rocm-cmake 提供的宏 =====
include(ROCMSetupVersion)
rocm_setup_version(VERSION 0.12.0)

# 断言版本号正确（rocm_setup_version 设置的是 ${PROJECT_NAME}_VERSION）
if(NOT test_package_VERSION VERSION_EQUAL "0.12.0")
    message(FATAL_ERROR "rocm_setup_version failed: expected 0.12.0, got ${test_package_VERSION}")
endif()

message(STATUS "✅ 鸿蒙消费者测试通过: rocm_setup_version OK, test_package_VERSION=${test_package_VERSION}")

add_executable(test_package test_package.cpp)
