cmake_minimum_required(VERSION 3.8)
project(test_eastdc LANGUAGES CXX)
enable_testing()
find_package(eastdc REQUIRED CONFIG)

# EAStdC 要求 user-provided 调试 operator new/delete（Config.h 契约），
# 消费者侧提供转发实现（与上游 EAStdCTest.cpp 同款做法）
add_library(ea_allocator STATIC ea_allocator_impl.cpp)
target_include_directories(ea_allocator PUBLIC ${eastdc_INCLUDE_DIRS})

# 消费者测试：仅通过 eastdc 公开头文件/API 编译、链接并运行
add_executable(test_consumer consumer_test.cpp)
target_link_libraries(test_consumer eastdc::eastdc ea_allocator)
add_test(NAME test_consumer COMMAND test_consumer)

# HarmonyOS 专项测试（#ifdef __OHOS__ 实质逻辑, R6）
add_executable(test_ohos_special ohos_special_test.cpp)
target_link_libraries(test_ohos_special eastdc::eastdc ea_allocator)
add_test(NAME test_ohos_special COMMAND test_ohos_special)
