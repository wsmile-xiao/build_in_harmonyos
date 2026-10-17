cmake_minimum_required(VERSION 3.15)
project(test_libjwt C)

# Find the package via Conan-generated CMakeDeps
find_package(libjwt REQUIRED)

add_executable(test_libjwt test.c)
target_link_libraries(test_libjwt libjwt::libjwt)

# 鸿蒙（OHOS）平台特有测试：SONAME 加载语义 / OpenSSL 静态链入 / /bin/sh 驱动
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos libjwt::libjwt ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_libjwt COMMAND test_libjwt)
