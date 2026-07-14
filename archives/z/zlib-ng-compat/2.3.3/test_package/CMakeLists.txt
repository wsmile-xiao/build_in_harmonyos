cmake_minimum_required(VERSION 3.15)
project(test_zlib-ng-compat C)

find_package(ZLIB REQUIRED)

add_executable(test_zlib-ng-compat test.c)
target_link_libraries(test_zlib-ng-compat ZLIB::ZLIB)

enable_testing()
add_test(NAME test_zlib-ng-compat COMMAND test_zlib-ng-compat)