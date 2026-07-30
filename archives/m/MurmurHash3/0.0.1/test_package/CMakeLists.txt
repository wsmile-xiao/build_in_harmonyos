cmake_minimum_required(VERSION 3.15)
project(test_murmurhash3 CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(murmurhash3 REQUIRED)

add_executable(test_murmurhash3 test.cpp)
target_link_libraries(test_murmurhash3 murmurhash3::murmurhash3)

enable_testing()
add_test(NAME test_murmurhash3 COMMAND test_murmurhash3)
