cmake_minimum_required(VERSION 3.16)
project(test_audiotube CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(audiotube REQUIRED)

add_executable(test_audiotube test.cpp)
target_link_libraries(test_audiotube PRIVATE audiotube::audiotube)

enable_testing()
add_test(NAME audiotube_test COMMAND test_audiotube)
