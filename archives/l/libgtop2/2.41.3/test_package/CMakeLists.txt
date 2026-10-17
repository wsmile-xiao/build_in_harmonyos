cmake_minimum_required(VERSION 3.15)
project(test_libgtop2 C)

# Conan CMakeDeps 生成的 libgtop2-config.cmake
find_package(libgtop2 REQUIRED)

# L1 消费者测试：通用 API 断言
add_executable(test_libgtop2_api test.c)
target_link_libraries(test_libgtop2_api libgtop2::libgtop2)

# 鸿蒙特有用例：OHOS procfs 语义断言（数量 >= 1，见 test_package/MANIFEST.yml）
add_executable(test_libgtop2_ohos test_ohos.c)
target_link_libraries(test_libgtop2_ohos libgtop2::libgtop2)

enable_testing()
add_test(NAME test_libgtop2_api COMMAND test_libgtop2_api)
add_test(NAME test_libgtop2_ohos COMMAND test_libgtop2_ohos)
