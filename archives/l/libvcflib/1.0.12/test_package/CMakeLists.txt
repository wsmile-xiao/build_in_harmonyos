# test_package — libvcflib 1.0.12 consumer test
cmake_minimum_required(VERSION 3.16)
project(test_libvcflib CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libvcflib CONFIG REQUIRED)

add_executable(test_libvcflib test_libvcflib.cpp)
target_link_libraries(test_libvcflib PRIVATE libvcflib::libvcflib)

enable_testing()
add_test(NAME consumer_parse COMMAND test_libvcflib "${CMAKE_CURRENT_SOURCE_DIR}/test.vcf")
