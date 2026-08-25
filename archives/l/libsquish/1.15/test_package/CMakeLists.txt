cmake_minimum_required(VERSION 3.15)
project(test_libsquish CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(libsquish REQUIRED)

add_executable(test_libsquish test_libsquish.cpp)
target_link_libraries(test_libsquish libsquish::libsquish)

enable_testing()
add_test(NAME test_libsquish COMMAND test_libsquish)
