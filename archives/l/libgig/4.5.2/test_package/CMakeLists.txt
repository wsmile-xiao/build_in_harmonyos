cmake_minimum_required(VERSION 3.15)
project(test_libgig CXX)

# Conan 的 CMakeDeps 生成 libgig-config.cmake（cpp_info.cmake_file_name=libgig），
# 目标名 libgig::libgig（cpp_info.cmake_target_name）。
find_package(libgig REQUIRED)

add_executable(test_libgig test_libgig.cpp)
target_link_libraries(test_libgig PRIVATE libgig::libgig)
set_target_properties(test_libgig PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_libgig COMMAND test_libgig)
