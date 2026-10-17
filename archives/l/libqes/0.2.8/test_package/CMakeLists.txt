cmake_minimum_required(VERSION 3.15)
project(test_libqes C)

find_package(libqes REQUIRED)
find_package(ZLIB REQUIRED)

add_executable(test_libqes test.c)
target_link_libraries(test_libqes libqes::libqes ZLIB::ZLIB)

enable_testing()
add_test(NAME test_libqes COMMAND test_libqes)
