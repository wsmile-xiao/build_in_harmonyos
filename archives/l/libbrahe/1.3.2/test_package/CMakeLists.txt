cmake_minimum_required(VERSION 3.15)
project(test_libbrahe LANGUAGES C)

find_package(libbrahe REQUIRED)

add_executable(test_libbrahe test_libbrahe.c)
target_link_libraries(test_libbrahe libbrahe::libbrahe)

enable_testing()
add_test(NAME test_libbrahe COMMAND test_libbrahe)
