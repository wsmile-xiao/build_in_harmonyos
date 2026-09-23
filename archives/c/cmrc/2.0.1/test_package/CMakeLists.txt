cmake_minimum_required(VERSION 3.15)
project(test_cmrc CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cmrc REQUIRED)

# 用法 1: 单资源嵌入 + 内容断言（注意：cmrc_add_resource_library 不接受
# FILES 关键字，资源路径直接作为未解析参数传入）
cmrc_add_resource_library(rc_hello NAMESPACE hello ${CMAKE_CURRENT_SOURCE_DIR}/hello.txt)

add_executable(test_cmrc test.cpp)
target_link_libraries(test_cmrc PRIVATE rc_hello)

enable_testing()
add_test(NAME test_cmrc COMMAND test_cmrc)

# 用法 2 (HarmonyOS 专项消费者测试): 目录迭代 + 存在性 + 异常路径断言
cmrc_add_resource_library(rc_ohos NAMESPACE ohos
    ${CMAKE_CURRENT_SOURCE_DIR}/hello.txt
    ${CMAKE_CURRENT_SOURCE_DIR}/subdir_a/subdir_b/file_b.txt
    )

add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos PRIVATE rc_ohos)

add_test(NAME test_ohos COMMAND test_ohos)