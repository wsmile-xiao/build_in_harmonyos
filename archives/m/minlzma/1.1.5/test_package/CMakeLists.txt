cmake_minimum_required(VERSION 3.15)
project(test_minlzma C)

# Find the package via Conan-generated CMakeDeps
find_package(minlzma REQUIRED)

# L1 消费者冒烟测试：内嵌 XZ 载荷，调用公共 API XzDecode
add_executable(test_minlzma test.c)
target_link_libraries(test_minlzma minlzma::minlzma)

# 鸿蒙专项测试：CRC32 流解压 + 损坏流错误处理 + 大小查询模式
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos minlzma::minlzma)

enable_testing()
add_test(NAME test_minlzma COMMAND test_minlzma)
add_test(NAME test_ohos COMMAND test_ohos)
