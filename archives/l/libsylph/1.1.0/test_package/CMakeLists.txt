cmake_minimum_required(VERSION 3.15)
project(test_libsylph C)

# 经 Conan CMakeDeps 找到被测包（libsylph 传递 glib 头/库）
find_package(libsylph REQUIRED)

add_executable(test_libsylph test.c)
target_link_libraries(test_libsylph libsylph::libsylph)

enable_testing()
add_test(NAME test_libsylph COMMAND test_libsylph)
