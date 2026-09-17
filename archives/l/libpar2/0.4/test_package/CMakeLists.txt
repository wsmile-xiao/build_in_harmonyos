cmake_minimum_required(VERSION 3.15)
project(test_libpar2 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 通过 Conan 生成的 CMakeDeps 查找被测包
find_package(libpar2 REQUIRED)
# libpar2.h 包含 <sigc++/sigc++.h>，直接依赖 libsigc（见 test_package/conanfile.py）
find_package(libsigc REQUIRED)

add_executable(test_libpar2 test_libpar2.cpp)
target_link_libraries(test_libpar2 libpar2::libpar2 libsigc::libsigc)

enable_testing()
add_test(NAME test_libpar2 COMMAND test_libpar2)
