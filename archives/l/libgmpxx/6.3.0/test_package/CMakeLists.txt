cmake_minimum_required(VERSION 3.15)
project(test_gmpxx CXX)

# Conan CMakeDeps 按 recipe 声明的 cmake_file_name 生成包配置；
# gmpxx.h 展开 #include <gmp.h>，两个包都显式 find + 链接
find_package(gmpxx CONFIG REQUIRED)
find_package(gmp CONFIG REQUIRED)

add_executable(test_gmpxx test_gmpxx.cpp)
target_link_libraries(test_gmpxx PRIVATE gmpxx::gmpxx gmp::gmp)
target_compile_features(test_gmpxx PRIVATE cxx_std_11)

enable_testing()
add_test(NAME gmpxx_bindings COMMAND test_gmpxx)
