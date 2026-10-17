cmake_minimum_required(VERSION 3.15)
project(test_libhdhomerun C)

find_package(libhdhomerun REQUIRED)

add_executable(test_libhdhomerun test.c)
target_link_libraries(test_libhdhomerun libhdhomerun::libhdhomerun)

enable_testing()
add_test(NAME test_libhdhomerun COMMAND test_libhdhomerun)
