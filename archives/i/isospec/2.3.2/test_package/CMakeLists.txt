cmake_minimum_required(VERSION 3.15)
project(test_isospec CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(isospec REQUIRED CONFIG)

add_executable(test_isospec test_isospec.cpp)
target_link_libraries(test_isospec isospec::isospec)

# 鸿蒙特有测试 (rule12): OHOS 动态加载器 + C API 消费回环
add_executable(test_isospec_ohos test_ohos.cpp)
target_link_libraries(test_isospec_ohos isospec::isospec ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_isospec COMMAND test_isospec)
add_test(NAME test_isospec_ohos COMMAND test_isospec_ohos)
