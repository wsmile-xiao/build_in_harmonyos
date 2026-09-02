cmake_minimum_required(VERSION 3.15)
project(test_efsw C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(efsw REQUIRED)

add_executable(test_efsw test.c)
target_link_libraries(test_efsw efsw::efsw)

# HarmonyOS 专项测试: generic 轮询后端
add_executable(test_efsw_generic test_generic.c)
target_link_libraries(test_efsw_generic efsw::efsw)

enable_testing()
add_test(NAME test_efsw COMMAND test_efsw)
add_test(NAME test_efsw_generic COMMAND test_efsw_generic)